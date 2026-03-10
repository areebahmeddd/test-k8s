# Project: FastAPI Todo API on Kubernetes

**Stack:** Python 3.11 · FastAPI · SQLAlchemy (async) · Alembic · uv · ruff · pytest  
**K8s layout:** `k8s/base/` (base manifests) + `k8s/overlays/dev|prod/` (Kustomize overlays)  
**Observability:** OpenTelemetry → Tempo (traces) · Loki (logs) · Prometheus (metrics) · Grafana (dashboards)

## Package Manager and Toolchain

- **Always** use `uv run <cmd>` to execute — never bare `python` or `pip`
- Install packages: `uv add <pkg>`, sync: `uv sync --frozen`
- Lint: `uv run ruff check app/ --fix` — Format: `uv run ruff format app/`
- Test: `uv run pytest -v --cov=app --cov-report=term-missing`
- Migrations: `uv run alembic revision --autogenerate -m "..."` then `uv run alembic upgrade head`

## Non-Negotiable Rules

- Type hints on every function signature — use `X | Y` unions, not `Optional[X]`
- No `print()` — use Python `logging` or `structlog`
- All new endpoints require a Pydantic schema in `app/schemas/`
- Secrets never in code, logs, or ConfigMaps — K8s Secrets + env vars only
- Ruff must pass (zero warnings) before any commit
- Every `async` function must properly `await` all coroutines

## Project Structure

- `app/models/` — SQLAlchemy ORM models only
- `app/schemas/` — Pydantic request/response schemas only
- `app/api/v1/` — Route handlers (thin — delegate to repository/service layer)
- `app/core/` — Config, database engine, security utilities
- `tests/unit/` — Pure logic tests (no I/O)
- `tests/integration/` — Full API tests via httpx AsyncClient
