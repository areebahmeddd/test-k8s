# AGENTS.md

Instructions for AI coding agents working in this repository. Documentation for people lives in
[README.md](README.md) and [docs/](docs/).

## Project

A FastAPI todo API (JWT authentication, async SQLAlchemy, Alembic) deployed to Kubernetes as a hands-on tour of
CNCF tooling: Kustomize, ArgoCD, CloudNativePG, Traefik, Calico NetworkPolicies, SOPS with age, OPA with
conftest, Tilt, Pulumi, and an observability stack where OpenTelemetry and Alloy feed Tempo, Loki and
Prometheus, all viewed in Grafana.

| Path            | Contents                                                                                |
| --------------- | --------------------------------------------------------------------------------------- |
| `app/`          | The FastAPI application: `api/v1/`, `core/`, `models/`, `schemas/` and the `static/` UI |
| `alembic/`      | Migrations; the app never creates tables at startup                                     |
| `tests/`        | `unit/` (no I/O) and `integration/` (httpx `AsyncClient` against SQLite)                |
| `k8s/base/`     | Manifests shared by every environment: `app`, `postgres`, `traefik`, `monitoring`       |
| `k8s/overlays/` | `dev` and `prod` patches, plus SOPS-encrypted `secrets/`                                |
| `k8s/argocd/`   | ArgoCD bootstrap per environment (`base/`, `dev/`, `prod/`)                             |
| `infra/`        | Pulumi program: an alternative bootstrap that takes secrets from Pulumi config          |
| `policy/`       | OPA policies run by conftest against the rendered overlays, with their unit tests       |

## Commands

Run everything through `uv`, never bare `python` or `pip`. `make help` lists every target.

```bash
uv sync                                                        # install (CI uses --locked)
uv run ruff check . --fix && uv run ruff format .
uv run pytest -v --cov=app                                     # no services needed
uv run alembic revision --autogenerate -m "describe the change"  # then review the generated file
uv run alembic upgrade head
make validate                                                  # manifests, schemas, SOPS, policies
```

Before calling work done, run the linter and the tests, and run `make validate` for any change under `k8s/` or
`policy/`.

## Rules

- Python 3.14, pinned by `requires-python`. Type-hint every signature, using `X | None`, built-in generics and
  `collections.abc`.
- Request and response bodies are Pydantic models in `app/schemas/`; ORM models live only in `app/models/`.
- Keep handlers small. Put shared lookups in a private helper (see `_get_owned_todo`), and add a service module
  only when the logic outgrows that.
- A resource owned by another user returns **404**, never 403, so ids are not disclosed.
- Every model change ships with an Alembic migration; CI runs `alembic check`.
- Log with `logging.getLogger(__name__)`. Logs are JSON and carry trace ids when tracing is on. Never use
  `print()`, and never log secrets, tokens or passwords.
- Configuration comes from environment variables through `app/core/config.py`. Secrets belong in Kubernetes
  Secrets, SOPS-encrypted in Git, and never in code, ConfigMaps or logs.
- Kubernetes changes keep the base environment-agnostic, put differences in the overlays and add NetworkPolicy
  rules for every new traffic path. The full checklist is in
  [.github/instructions/kubernetes.instructions.md](.github/instructions/kubernetes.instructions.md).
- A release bumps the version in `pyproject.toml`, `app/core/config.py`, the `Makefile` image tag and the image
  and version label in `k8s/base/app/todo-api-deployment.yaml` together, then publishes the image with
  `make image-push`.
- Never commit `age.key`, `.env` or a decrypted secret. Edit secrets with `sops <file>`.

## Customizations

Copilot reads these from `.github/`, alongside this file:

- `instructions/`: rules scoped by `applyTo` for Python, API routes, tests, Kubernetes, Docker and GitHub Actions
- `agents/`: `architect` for design and trade-offs (read-only) and `reviewer` for adversarial pre-merge review
- `skills/`: `clean-code` and `conventional-commit`
