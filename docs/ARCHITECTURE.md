# Architecture

## Code layout

```text
app/
  main.py              Creates the app: telemetry, routers, /health, /metrics and the UI at /
  core/
    config.py          Settings read from environment variables and .env (SECRET_KEY is required)
    database.py        Async engine, session factory and the get_db dependency
    security.py        Password hashing, JWT access tokens, refresh token generation and hashing
    telemetry.py       JSON logging, plus OTLP tracing of FastAPI and SQLAlchemy when enabled
  api/
    deps.py            DbDep and CurrentUser dependencies
    v1/
      router.py        Mounts the routers below at /api/v1
      auth.py          /auth: register, login, refresh, logout, me
      todos.py         /todos: list, create, get, update, delete
  models/
    base.py            Declarative base and the created_at/updated_at mixin
    user.py            User
    todo.py            Todo and the Priority enum
    refresh_token.py   RefreshToken
  schemas/             Pydantic request and response models
  static/              Single-page web UI, served from the same origin as the API
alembic/
  env.py               Async migration runner
  versions/            Migration scripts
tests/
  conftest.py          Fixtures: test client, database session, user and tokens
  unit/                Pure functions, no I/O
  integration/         HTTP tests against the app, with a fresh SQLite database per test
```

Alembic owns the schema; the app never creates tables. Docker Compose runs `alembic upgrade head` before
starting the server, and in Kubernetes a `migrate` init container does the same. On PostgreSQL, migration runs
take an advisory lock, so replicas that start at the same time wait for each other instead of racing.

## Database schema

Every primary key is a UUID, and every table has `created_at` and `updated_at` timestamps set by the database.

| Table            | Columns                                                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `users`          | `email` (unique), `username` (unique, stored lowercase), `hashed_password`, `is_active`                                                    |
| `todos`          | `title`, `description` (optional), `completed`, `priority` (`low`, `medium` or `high`; default `medium`), `due_date` (optional), `user_id` |
| `refresh_tokens` | `token_hash` (SHA-256, unique), `user_id`, `expires_at`, `revoked`                                                                         |

Both `user_id` columns are indexed foreign keys to `users` with `ON DELETE CASCADE`.

## Authentication

1. **Register.** The email must be valid, the username may contain only letters, digits and underscores (it is
   stored lowercase), and the password must be 8 to 72 bytes long. The password is hashed with bcrypt. A
   duplicate email or username violates a unique constraint and returns 409.
2. **Log in.** The OAuth2 password form returns a JWT access token valid for 30 minutes (claims `sub`, `exp`
   and `type=access`) and an opaque refresh token valid for 7 days. Only the SHA-256 hash of the refresh token
   is stored. When the username does not exist, bcrypt still runs against a dummy hash, so response times do
   not reveal which usernames are registered.
3. **Call a protected route.** `CurrentUser` checks the signature, expiry and `type` of the access token, then
   loads the user. Missing or inactive users get 401.
4. **Refresh.** A single atomic statement revokes the presented token, but only if it is still valid:
   `UPDATE refresh_tokens SET revoked = true WHERE token_hash = :hash AND NOT revoked AND expires_at > now() RETURNING user_id`.
   A replayed token, or the same token used twice at once, therefore gets 401. Inactive users cannot refresh.
   Whenever tokens are issued, the user's revoked and expired tokens are deleted, so the table stays small.
5. **Log out.** The given refresh token is revoked and the endpoint returns 204, even if the token was unknown.
   Access tokens are stateless and simply expire.

## Design decisions

- **Async throughout.** The asyncpg and aiosqlite drivers, `AsyncSession` and async handlers keep request
  handling non-blocking.
- **404 for other users' todos.** Someone else's todo looks exactly like a missing one, so ids are not disclosed.
- **Constraints instead of pre-checks.** Uniqueness and token rotation rely on the database, which avoids
  check-then-act races.
- **Opt-in tracing.** Tracing starts only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Log lines then include
  `trace_id` and `span_id`, which lets Grafana jump from a trace to its logs.
- **SQLite for tests.** Each test gets its own database file through an override of `get_db` in
  `tests/conftest.py`, so the suite needs no services.
- **bcrypt off the event loop.** Hashing takes a few hundred milliseconds by design, so it runs in a worker
  thread and other requests on the same pod keep flowing. Registration rejects passwords over 72 bytes and
  login treats them as a mismatch, rather than letting bcrypt raise an error.
