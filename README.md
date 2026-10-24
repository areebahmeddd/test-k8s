# Todo API on Kubernetes

A small FastAPI todo API with JWT authentication, rotating refresh tokens, async SQLAlchemy and Alembic. It
serves as a hands-on project for the CNCF ecosystem: GitOps with ArgoCD, PostgreSQL with CloudNativePG, Traefik
ingress, Calico NetworkPolicies, SOPS secrets, OPA policies, Tilt, Pulumi and an OpenTelemetry and Grafana
observability stack.

## Roadmap

- [ ] TLS with cert-manager, and authentication for the internal tool ingresses
- [ ] Move the policy checks from OPA and conftest to Kyverno
- [ ] Service mesh with Linkerd (mTLS and traffic policies)
- [ ] Event-driven autoscaling of `todo-api` with KEDA
- [ ] Authentik as the identity provider, with single sign-on for Grafana and ArgoCD
- [ ] Chaos experiments with LitmusChaos

## Stack

| Layer           | Technology                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| API             | Python 3.14, FastAPI, Pydantic 2, SQLAlchemy 2.0 (async), Alembic                                   |
| Authentication  | PyJWT (HS256) access tokens, opaque rotating refresh tokens, bcrypt                                 |
| Tooling         | uv, Ruff, pytest, pre-commit                                                                        |
| Database        | PostgreSQL 18 on CloudNativePG 1.30 with PgBouncer; SQLite for tests                                |
| Delivery        | Kustomize, ArgoCD 3.5, Tilt for local development, Pulumi as an optional bootstrap                  |
| Networking      | Traefik 3.7, Calico NetworkPolicies (default deny)                                                  |
| Secrets, policy | SOPS with age, OPA policies with conftest, kubeconform                                              |
| Observability   | OpenTelemetry and Alloy, Tempo 3 for traces, Loki for logs, Prometheus and Alertmanager, Grafana 13 |

## Quick start

```bash
cp .env.example .env        # then set SECRET_KEY, for example with: openssl rand -hex 32
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

The web UI is at <http://localhost:8000> and the interactive API docs are at <http://localhost:8000/docs>.
The tests need no services:

```bash
make test
```

Every `make` target is a shortcut for plain commands: `make -n <target>` prints them without running anything.

### Docker

With PostgreSQL, through Docker Compose (migrations run on start and code changes reload the server):

```bash
make up              # docker compose up -d --build; stop with: make down
```

Or the image on its own, with SQLite. The container runs as a non-root user, so the database goes in `/tmp`:

```bash
docker build -t todo-api:local .
docker run --rm -p 8000:8000 --env-file .env -e DATABASE_URL=sqlite+aiosqlite:////tmp/todo.db \
  todo-api:local sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### Kubernetes

```bash
make cluster-up      # minikube with Calico
tilt up              # build, deploy the dev overlay, rebuild on every change
```

[docs/KUBERNETES.md](docs/KUBERNETES.md) covers every deployment option: Tilt, plain `kubectl`, GitOps with
ArgoCD, and Pulumi.

## API

| Method | Path                    | Description                                                       |
| ------ | ----------------------- | ----------------------------------------------------------------- |
| POST   | `/api/v1/auth/register` | Create an account                                                 |
| POST   | `/api/v1/auth/login`    | Exchange a username and password (OAuth2 form) for a token pair   |
| POST   | `/api/v1/auth/refresh`  | Exchange a refresh token for a new token pair                     |
| POST   | `/api/v1/auth/logout`   | Revoke a refresh token                                            |
| GET    | `/api/v1/auth/me`       | Return the current user                                           |
| GET    | `/api/v1/todos`         | List your todos, newest first (`offset` and `limit`, at most 100) |
| POST   | `/api/v1/todos`         | Create a todo                                                     |
| GET    | `/api/v1/todos/{id}`    | Get a todo                                                        |
| PATCH  | `/api/v1/todos/{id}`    | Update some fields of a todo                                      |
| DELETE | `/api/v1/todos/{id}`    | Delete a todo                                                     |
| GET    | `/health`               | Health check used by the Kubernetes probes                        |
| GET    | `/metrics`              | Prometheus metrics                                                |

The todo routes require an `Authorization: Bearer <access_token>` header. Another user's todo returns 404.

## Repository layout

```text
app/            FastAPI app: routes, configuration, database, security, telemetry, models, schemas, web UI
alembic/        Database migrations
tests/          Unit and integration tests
k8s/            Kustomize bases, dev and prod overlays, ArgoCD bootstrap (see k8s/README.md)
infra/          Pulumi bootstrap program
policy/         OPA policies and their tests
docs/           Architecture, Kubernetes, observability, troubleshooting and k9s guides
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md): code layout, database schema, authentication, design decisions
- [Kubernetes](docs/KUBERNETES.md): cluster setup, deployment options, secrets, networking, validation
- [Observability](docs/OBSERVABILITY.md): metrics, logs, traces, alerts and dashboards
- [Troubleshooting](docs/TROUBLESHOOTING.md) and a [k9s cheat sheet](docs/K9S.md)
- [Pulumi bootstrap](infra/README.md)
