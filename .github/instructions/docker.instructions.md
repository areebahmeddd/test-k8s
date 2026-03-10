---
name: Docker Best Practices
description: "Use when writing or reviewing Dockerfiles or docker-compose files. Covers multi-stage builds, layer caching optimization, non-root user, image pinning, .dockerignore, and security hardening."
applyTo: "{Dockerfile,Dockerfile.*,docker-compose.yaml,docker-compose.yml,docker-compose*.yaml,docker-compose*.yml}"
---

# Docker Best Practices

## Multi-Stage Builds (Required for Production Images)

Use separate stages for building/installing dependencies and the final runtime image. The runtime image should contain NO build tools.

```dockerfile
# Stage 1: Install dependencies (build tools available here)
FROM python:3.11-slim AS builder
WORKDIR /app

RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Runtime (minimal — no pip, no uv, no build tools)
FROM python:3.11-slim AS runtime
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"
```

## Non-Root User (Required)

```dockerfile
RUN groupadd --gid 1000 appuser \
 && useradd --uid 1000 --gid appuser --shell /bin/sh --create-home appuser

USER appuser
```

Add before `COPY`/`CMD` in the runtime stage. Combine `RUN` commands with `&&` to minimize layers.

## Layer Caching — Copy Order Matters

```dockerfile
# CORRECT: dependency files first → deps cached until pyproject.toml changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# THEN: app source (cache invalidated only when code changes)
COPY app/ ./app/
```

Never `COPY . .` before installing dependencies — it breaks layer caching on every code change.

## Base Image Rules

- Use `-slim` variants: `python:3.11-slim` not `python:3.11`
- Pin to a specific version tag: `python:3.11.9-slim` not `python:3.11-slim` in production
- For maximum reproducibility, pin to digest: `python:3.11-slim@sha256:<hash>`
- Never use `:latest` in production — it changes without warning

## Security

- No secrets in `Dockerfile` — use Docker secrets or environment variables at runtime
- `--no-cache-dir` for pip if used directly: `RUN pip install --no-cache-dir uvicorn`
- Don't install dev dependencies in the production image: `uv sync --no-dev`
- Minimize the layers that run as root — switch to non-root as early as possible

## docker-compose.yaml

- Always set `restart: unless-stopped` for persistent services
- Never hardcode secrets — use `.env` file with `env_file:` directive
- Explicit named networks for service isolation
- Named volumes for persistent data (not host bind mounts for anything important)
- Set `healthcheck:` on services that other services depend on
- Use `depends_on: { service: { condition: service_healthy } }` not just `depends_on: [service]`

## .dockerignore (Always Present)

```
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.git/
.github/
tests/
docs/
*.md
.env
.env.*
```

Not having `.dockerignore` sends the entire `.git` folder into the build context — slow and leaks history.
