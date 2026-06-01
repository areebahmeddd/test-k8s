# Docker Best Practices

## Multi-Stage Builds (Required for Production Images)

```dockerfile
# Stage 1: build / dependency installation
FROM python:3.11-slim AS builder
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ ./app/
RUN uv sync --frozen --no-dev

# Stage 2: minimal runtime — no pip, no uv, no build tools
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

## Layer Caching — Copy Order Matters

```dockerfile
# CORRECT: deps first → cached until pyproject.toml changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# THEN: source code (cache only invalidated on code changes)
COPY app/ ./app/
```

## Rules

- Pin base images to a specific digest or version tag — never `latest`
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`
- Combine `RUN` commands with `&&` to minimize layers
- Always include a `.dockerignore` excluding `.venv/`, `__pycache__/`, `.pytest_cache/`
