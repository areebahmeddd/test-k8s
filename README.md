# Todo API

A REST API for managing todos with user authentication. Built with FastAPI, SQLAlchemy (async), and JWT-based auth using short-lived access tokens and rotating refresh tokens.

## Roadmap

- [ ] Migrate observability stack to LGTM (Loki, Grafana, Tempo, Mimir)
- [ ] Migrate policy engine from OPA to Kyverno
- [ ] Service mesh with Linkerd (mTLS, traffic policies, observability)
- [ ] KEDA for event-driven autoscaling of the todo-api deployment
- [ ] Authentik as the identity provider (SSO, OIDC, Grafana/ArgoCD login)
- [ ] Litmus Chaos for chaos engineering experiments

## Stack

| Layer      | Technology                              |
| ---------- | --------------------------------------- |
| Framework  | FastAPI (async)                         |
| ORM        | SQLAlchemy 2 with async engine          |
| Database   | PostgreSQL (prod) / SQLite (dev, tests) |
| Auth       | PyJWT (HS256) + bcrypt                  |
| Migrations | Alembic                                 |
| Packaging  | uv                                      |
| Linting    | Ruff                                    |
| Tests      | pytest + pytest-asyncio + httpx         |
| Metrics    | Prometheus + Alertmanager               |
| Logs       | Loki + Promtail                         |
| Traces     | Tempo + OTel Collector (contrib)        |
| Dashboards | Grafana                                 |

- See [docs/markdown/SETUP-py.md](docs/markdown/SETUP-py.md) for local Python setup, Docker, migrations, and environment configuration.
- See [docs/markdown/SETUP-k8s.md](docs/markdown/SETUP-k8s.md) for Kubernetes deployment.
- See [docs/markdown/MONITORING.md](docs/markdown/MONITORING.md) for the observability stack (metrics, logs, traces).

## API Endpoints

### Auth — `/api/v1/auth`

| Method | Path        | Description                                      |
| ------ | ----------- | ------------------------------------------------ |
| POST   | `/register` | Create a new user account                        |
| POST   | `/login`    | Authenticate and receive access + refresh tokens |
| POST   | `/refresh`  | Exchange a refresh token for a new token pair    |
| POST   | `/logout`   | Revoke the current refresh token                 |
| GET    | `/me`       | Return the currently authenticated user          |

### Todos — `/api/v1/todos`

| Method | Path    | Description                       |
| ------ | ------- | --------------------------------- |
| GET    | `/`     | List all todos for the caller     |
| POST   | `/`     | Create a new todo                 |
| GET    | `/{id}` | Get a single todo by ID           |
| PATCH  | `/{id}` | Update fields on an existing todo |
| DELETE | `/{id}` | Delete a todo                     |

All todo endpoints require a valid `Authorization: Bearer <access_token>` header. Users can only access their own todos.

### Other

| Method | Path      | Description    |
| ------ | --------- | -------------- |
| GET    | `/health` | Liveness check |

## Quick Start

### Docker

```bash
make up
# or
docker compose up
```

The `api` service waits for the `db` service health check before starting. Database URL is injected via environment in `docker-compose.yaml`.

Monitoring services (Prometheus, Loki, Tempo, Grafana, etc.) are defined in `docker-compose.yaml` but commented out — they are deployed separately via Kubernetes. (You can uncomment them for local testing)

### Running Tests

```bash
make test
# or
uv run pytest -v
```

Tests use an in-memory SQLite database and a fresh schema per test session. No running server or database required.

## Project Layout

```
app/
  main.py               Application factory, lifespan, CORS
  core/
    config.py           Settings (loaded from .env)
    database.py         Async engine, session, get_db dependency
    security.py         Password hashing and JWT utilities
  models/               SQLAlchemy ORM models
  schemas/              Pydantic request/response schemas
  api/
    deps.py             FastAPI dependencies (current user)
    v1/
      auth.py           Auth route handlers
      todos.py          Todo route handlers
      router.py         Router registration
alembic/                Migration environment and versions
tests/
  conftest.py           Shared fixtures
  unit/                 Pure function tests
  integration/          Full HTTP endpoint tests
docs/
  SETUP.md              Detailed local setup guide
  architecture.md       DB schema and auth flow reference
```
