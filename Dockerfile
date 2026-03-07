# Build:
#   docker build -t todo-api:latest .
#
# Run (standalone with SQLite):
#   docker run -d -p 8000:8000 --name todo-api --env-file .env todo-api:latest
#
# Run (with external PostgreSQL):
#   docker run -d -p 8000:8000 --name todo-api --env-file .env \
#     -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname \
#     todo-api:latest

# Stage 1: Build the application with dependencies
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# cache deps layer separately from source
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev

# Stage 2: Runtime image with only the necessary files
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
