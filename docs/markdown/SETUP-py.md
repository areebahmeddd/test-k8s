# Setup Guide for Python Development

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) — dependency management and tooling
- Docker and Docker Compose — only for the containerised setup

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

## Local Development (UV)

Uses SQLite by default. No external services required.

```bash
uv sync                          # install all dependencies including dev group
cp .env.example .env             # edit if needed
make upgrade                     # apply migrations
uv run fastapi dev app/main.py   # start server with hot reload
```

## Local Development (Docker)

Starts the API and a PostgreSQL database together.

```bash
make up     # docker compose up -d
make down   # stop and remove containers
```

`DATABASE_URL` is set automatically inside `docker-compose.yaml`. Everything else is read from your `.env` file.

To apply migrations inside the running container:

```bash
docker compose exec api alembic upgrade head
```

The server is available at `http://localhost:8000`
Interactive docs at `/docs` (Swagger) and `/redoc` (ReDoc)

## Database Migrations (Alembic)

```bash
make migrate msg="add priority column to todos"    # generate a new revision
make upgrade                                       # apply all pending migrations
make downgrade                                     # roll back the last migration
```

## Testing

```bash
make test                          # run all tests with coverage
uv run pytest tests/unit -v        # unit tests only
uv run pytest tests/integration -v # integration tests only
```

Tests use an in-memory SQLite database. No external services required.

## Code Quality

```bash
uv run pre-commit install   # install hooks once (runs automatically on git commit)
make quality                # run all hooks manually against all files
```

Hooks: `ruff` (lint + format), `check-yaml`, `trailing-whitespace`, `end-of-file-fixer`.
