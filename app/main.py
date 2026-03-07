from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

import app.models  # noqa: F401
from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.telemetry import setup_telemetry
from app.models.base import Base


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # pragma: no cover
    """Create all database tables on startup and dispose the engine on shutdown."""
    setup_telemetry(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(api_v1_router)

Instrumentator().instrument(app).expose(app, include_in_schema=False)

app.mount("/", StaticFiles(directory="docs", html=True), name="ui")


@app.get("/health", tags=["system"], status_code=status.HTTP_200_OK)
async def health() -> JSONResponse:
    """Return application health status and current version."""
    return JSONResponse(
        content={"status": "ok", "version": settings.version},
    )
