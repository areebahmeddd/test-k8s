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

## Available Customizations

**Agents** (`.claude/skills/`) — invoke by name for specialized modes:

- `architect` — system design, ADRs, component diagrams, technology tradeoffs
- `reviewer` — adversarial security/correctness/performance review before merging

**Rules** (`.claude/rules/`) — auto-applied per file type:

- `python.md` → all `**/*.py` files
- `kubernetes.md` → all `k8s/**` files
- `docker.md` → Dockerfiles and docker-compose files
- `github-actions.md` → `.github/workflows/**` files
- `testing.md` → `tests/**` and `conftest.py`
- `api-design.md` → `app/api/**` files

**Skills** (`.claude/skills/`) — invoke by name for focused guidance:

- `brand-guidelines` — color tokens, typography scale, design system, visual consistency
- `clean-code` — naming, Clean Code principles, code smells, function size
- `code-review` — correctness, security, performance, maintainability review
- `conventional-commit` — commit messages, changelog, PR descriptions
- `deep-thinking` — first-principles reasoning, complex problems, architecture tradeoffs
- `frontend-design` — web UI components, pages, dashboards, CSS/React/Next.js
- `quasi-coder` — convert pseudo-code or rough ideas into production implementation
- `refactor` — restructure without behavior change, extract functions, reduce complexity
- `solid-principles` — OOP design, SOLID violations, coupling, testability
- `web-performance` — Core Web Vitals, SEO, GEO, llms.txt, rendering strategy

## MCP Tools

- **context7** — use `mcp_context7_resolve-library-id` + `mcp_context7_query-docs` to fetch up-to-date library documentation before writing code that uses any third-party package. Always prefer this over relying on training-data knowledge for library APIs.
- **sequential-thinking** — use `mcp_sequentialthi_sequentialthinking` for multi-step reasoning on complex problems: architecture decisions, debugging hard issues, planning a sequence of changes. Prefer this when the problem has more than two or three interdependent steps.
