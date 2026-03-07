# Setup Guide for Python Development

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) — used for dependency management and running tools
- Docker and Docker Compose — optional, for the containerised setup
- PostgreSQL 16 — only if running locally without Docker

## Environment Variables

Create a `.env` file in the project root. All variables are optional and fall back to the defaults shown below.

```ini
APP_NAME=Todo API
DEBUG=false

# SQLite is used by default for local development.
# For PostgreSQL, use the asyncpg driver.
DATABASE_URL=sqlite+aiosqlite:///./todo.db

# Change this to a randomly generated 32-byte hex string in any non-trivial environment.
SECRET_KEY=11b0af168eccd3d094806723b164d81ee230764194226773a3c32028b31ab77d

ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

For PostgreSQL:

```ini
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>
```

## Local Development (without Docker)

```bash
# 1. Install all dependencies including dev group
uv sync

# 2. Set up environment
cp .env.example .env   # edit if needed

# 3. Apply migrations (creates tables)
make upgrade

# 4. Start the development server
make up
```

The server starts at `http://localhost:8000` with hot reload enabled.

Interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Setup

```bash
# Start the API server and a PostgreSQL 16 database
docker compose up --build
```

This starts two services:

- `db` — PostgreSQL with a health check
- `api` — the FastAPI application, waits for `db` to be healthy before starting

The `DATABASE_URL` environment variable is set automatically inside `docker-compose.yaml` to point at the `db` service. All other configuration is read from your `.env` file via `env_file: .env`.

To apply migrations after the containers are running:

```bash
docker compose exec api alembic upgrade head
```

## Database Migrations

Generate a new revision after changing models:

```bash
make migrate msg="add priority column to todos"
```

Apply all pending migrations:

```bash
make upgrade
```

Roll back the most recent migration:

```bash
make downgrade
```

## Running Tests

```bash
make test
# or
uv run pytest -v
```

Tests override the `get_db` dependency with an in-memory SQLite database. A fresh schema is created at the start of each test session. No external services are required.

To run only unit tests:

```bash
uv run pytest tests/unit -v
```

To run only integration tests:

```bash
uv run pytest tests/integration -v
```

## Linting and Formatting

```bash
# Run all pre-commit hooks (lint, format, checks)
make quality
```

To run ruff directly:

```bash
# Lint
uv run ruff check app tests

# Format
uv run ruff format app tests
```

Configuration is in `pyproject.toml`.

## Pre-commit Hooks

Install the hooks once:

```bash
uv run pre-commit install
```

After that, hooks run automatically on every `git commit`. To run them manually against all files:

```bash
make quality
```

Hooks configured:

- `ruff` — lint check with auto-fix
- `ruff-format` — code formatting
- `check-yaml` — YAML syntax check
- `trailing-whitespace` — strip trailing spaces
- `end-of-file-fixer` — ensure files end with a newline
