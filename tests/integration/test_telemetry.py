import json
import os
import subprocess
import sys

# Tracing installs process-global providers and instrumentation, so it runs in a fresh
# interpreter. The script emits a log line inside a request span and prints the result.
_PROBE = """
import asyncio, json, logging, sys
import httpx
from opentelemetry import trace
from app.main import app

logs = []
handler = logging.getLogger().handlers[0]
handler.emit = lambda record: logs.append(handler.format(record))

async def probe() -> dict[str, str]:
    logging.getLogger("probe").info("inside request")
    return {}

# Register ahead of the static UI mounted at "/", which would otherwise shadow it.
app.router.add_api_route("/probe", probe)
app.router.routes.insert(0, app.router.routes.pop())

async def main() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        await c.get("/probe")

asyncio.run(main())
print(json.dumps({
    "provider": type(trace.get_tracer_provider()).__name__,
    "log": json.loads(next(line for line in logs if "inside request" in line)),
}))
"""


def _run_probe(**env: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_tracing_enabled_adds_trace_ids_to_logs():
    """Assert that an OTLP endpoint turns on tracing and request logs carry the span's ids."""
    result = _run_probe(
        OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:1",
        OTEL_SERVICE_NAME="todo-api-test",
        OTEL_BSP_SCHEDULE_DELAY="600000",
    )
    assert result["provider"] == "TracerProvider"
    assert len(result["log"]["trace_id"]) == 32
    assert result["log"]["trace_id"] != "0" * 32
    assert result["log"]["service_name"] == "todo-api-test"


def test_tracing_disabled_without_endpoint():
    """Assert that without an OTLP endpoint no tracer is installed and logs stay plain."""
    result = _run_probe(OTEL_EXPORTER_OTLP_ENDPOINT="")
    assert result["provider"] == "ProxyTracerProvider"
    assert "trace_id" not in result["log"]
