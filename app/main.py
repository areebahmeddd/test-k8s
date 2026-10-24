from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.telemetry import setup_telemetry

STATIC_DIR = Path(__file__).parent / "static"

# The library's default buckets stop at 1 s, which would cap latency percentiles and make the
# SlowP99Latency alert (p99 > 1 s) impossible to fire.
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:  # pragma: no cover
    """Dispose the database engine on shutdown. The schema is managed by Alembic."""
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Instrument before the first request: the middleware stack is built on startup.
setup_telemetry(app, engine)

app.include_router(api_v1_router)

Instrumentator(excluded_handlers=["/health", "/metrics"]).add(
    metrics.default(latency_lowr_buckets=LATENCY_BUCKETS)
).instrument(app).expose(app, include_in_schema=False)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return application health status and current version."""
    return {"status": "ok", "version": settings.version}


# Mounted last so API routes take precedence over the static UI.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
