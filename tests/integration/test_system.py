from httpx import AsyncClient


async def test_health(client: AsyncClient):
    """Assert that the health endpoint reports ok with the app version."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_metrics_exposed(client: AsyncClient):
    """Assert that metrics are served, with latency buckets wide enough for the 1 s alert."""
    await client.get("/api/v1/todos")
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
    assert 'http_request_duration_seconds_bucket{handler="/api/v1/todos",le="10.0"' in resp.text


async def test_static_ui_served_at_root(client: AsyncClient):
    """Assert that the bundled web UI is served at the root path."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
