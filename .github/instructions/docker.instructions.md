---
name: Docker
description: Conventions for the Dockerfile and docker-compose.yaml.
applyTo: "**/Dockerfile,**/docker-compose*.yaml,**/.dockerignore"
---

# Docker

- Multi-stage build: the builder installs dependencies with a pinned `uv` image
  (`uv sync --locked --no-dev --no-install-project`, cache and bind mounts); the runtime stage copies only
  `.venv`, `app/`, `alembic/` and `alembic.ini`.
- `.dockerignore` is an allow-list; add a path there when the image needs it.
- Run as the non-root `app` user (UID/GID 1000, matching the Kubernetes `securityContext`).
- Pin base and tool images to explicit versions; never `:latest`.
- Compose is for local development only: the API with `--reload` plus PostgreSQL with a healthcheck,
  `depends_on: condition: service_healthy`, and secrets from `.env`.
