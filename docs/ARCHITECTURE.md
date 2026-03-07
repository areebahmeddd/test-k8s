# Architecture

## Project Structure

```
app/
  main.py               FastAPI app instance, lifespan handler, CORS, health endpoint
  core/
    config.py           Pydantic Settings class; loads from .env at startup
    database.py         Async SQLAlchemy engine, session factory, get_db dependency
    security.py         Password hashing (bcrypt), JWT creation/decoding, refresh token generation
  models/
    base.py             DeclarativeBase + TimestampMixin (created_at, updated_at)
    user.py             User ORM model
    todo.py             Todo ORM model + Priority enum
    refresh_token.py    RefreshToken ORM model
  schemas/
    auth.py             Token, RefreshRequest Pydantic schemas
    user.py             UserCreate, UserRead Pydantic schemas
    todo.py             TodoCreate, TodoUpdate, TodoRead Pydantic schemas
  api/
    deps.py             get_current_user dependency; CurrentUser and DbDep type aliases
    v1/
      auth.py           /register, /login, /refresh, /me route handlers
      todos.py          CRUD route handlers for todos
      router.py         Registers auth and todos routers under /api/v1
alembic/
  env.py                Async-compatible Alembic runner
  versions/             Migration scripts
tests/
  conftest.py           pytest fixtures — test client, registered user, auth tokens
  unit/                 Pure function tests (security utilities)
  integration/          Full HTTP tests via httpx AsyncClient
```

## Database Schema

Three tables. All primary keys are UUID v4. All tables include `created_at` and `updated_at` timestamps via `TimestampMixin`.

### `users`

| Column            | Type        | Constraints               |
| ----------------- | ----------- | ------------------------- |
| `id`              | UUID        | PK                        |
| `email`           | VARCHAR     | UNIQUE, INDEXED, NOT NULL |
| `username`        | VARCHAR     | UNIQUE, INDEXED, NOT NULL |
| `hashed_password` | VARCHAR     | NOT NULL                  |
| `is_active`       | BOOLEAN     | DEFAULT true              |
| `created_at`      | TIMESTAMPTZ | auto-set on insert        |
| `updated_at`      | TIMESTAMPTZ | auto-updated on change    |

### `todos`

| Column        | Type        | Constraints                             |
| ------------- | ----------- | --------------------------------------- |
| `id`          | UUID        | PK                                      |
| `title`       | VARCHAR     | NOT NULL                                |
| `description` | TEXT        | nullable                                |
| `completed`   | BOOLEAN     | DEFAULT false                           |
| `priority`    | ENUM        | `low`, `medium`, `high` — DEFAULT `low` |
| `due_date`    | DATE        | nullable                                |
| `user_id`     | UUID        | FK → `users.id` (CASCADE DELETE)        |
| `created_at`  | TIMESTAMPTZ | auto-set on insert                      |
| `updated_at`  | TIMESTAMPTZ | auto-updated on change                  |

### `refresh_tokens`

| Column       | Type        | Constraints                      |
| ------------ | ----------- | -------------------------------- |
| `id`         | UUID        | PK                               |
| `token_hash` | VARCHAR     | UNIQUE, INDEXED, NOT NULL        |
| `user_id`    | UUID        | FK → `users.id` (CASCADE DELETE) |
| `expires_at` | TIMESTAMPTZ | NOT NULL                         |
| `revoked`    | BOOLEAN     | DEFAULT false                    |
| `created_at` | TIMESTAMPTZ | auto-set on insert               |
| `updated_at` | TIMESTAMPTZ | auto-updated on change           |

The raw refresh token is never stored. Only its SHA-256 hash is persisted. The plaintext token is transmitted once over the wire and then discarded.

## Auth Flow

### 1. Registration — `POST /api/v1/auth/register`

1. Validate `UserCreate` input (email format, username alphanumeric, minimum password length).
2. Check that neither email nor username already exists in `users`.
3. Hash the password with bcrypt and insert a new `User` row.
4. Return `UserRead` (no tokens issued).

### 2. Login — `POST /api/v1/auth/login`

Accepts `application/x-www-form-urlencoded` (OAuth2 password form).

1. Look up user by username.
2. Verify the submitted password against the stored bcrypt hash.
3. Generate a signed JWT access token (`sub=<user_id>`, `exp=now+30m`, `type=access`).
4. Generate a UUID4 refresh token, hash it with SHA-256, and insert a `RefreshToken` row with `expires_at=now+7d`.
5. Return `Token` — both the plaintext access and refresh tokens.

### 3. Accessing Protected Routes

Every protected endpoint declares a `CurrentUser` dependency.

1. Extract the `Authorization: Bearer <token>` header.
2. Decode and verify the JWT (`HS256`, checks `exp`, checks `type == "access"`).
3. Load the `User` row from the database using the `sub` claim.
4. Reject if user is not found or `is_active` is false.

### 4. Token Refresh — `POST /api/v1/auth/refresh`

1. Accept the plaintext refresh token in the request body.
2. Hash it with SHA-256 and query `refresh_tokens` by hash.
3. Reject if not found, already revoked, or expired.
4. Mark the existing token row as `revoked=True`.
5. Issue a new access token and a new refresh token.
6. Store the new refresh token hash in a new `RefreshToken` row.
7. Return the new `Token` pair.

Each refresh invalidates the previous refresh token (rotation). If a stolen token is used after rotation, the attempt fails immediately.

### 5. Logout / Revocation

There is no explicit logout endpoint. Refresh tokens are revoked on rotation. Access tokens expire after 30 minutes and cannot be individually revoked (stateless JWTs). For production, add a blocklist or reduce the access token TTL.

## Request Lifecycle

```
Client
  ├── POST /api/v1/auth/login
  │     └── Returns { access_token, refresh_token }
  │
  ├── GET /api/v1/todos
  │     Authorization: Bearer <access_token>
  │     ├── deps.get_current_user decodes JWT
  │     ├── Loads User from DB
  │     └── Handler queries todos WHERE user_id = current_user.id
  │
  └── POST /api/v1/auth/refresh
        body: { refresh_token: "<old_token>" }
        ├── SHA-256 hash lookup in refresh_tokens
        ├── Old token revoked
        └── Returns new { access_token, refresh_token }
```

## Design Decisions

**Async throughout.** The engine, sessions, and all route handlers are async. This avoids thread-pool overhead and keeps latency predictable under I/O-bound load.

**Refresh token hashing.** Storing the raw UUID in the database would allow anyone with read access to the database to replay tokens. Storing only the SHA-256 hash means a database breach does not expose valid tokens.

**Token rotation.** Each call to `/refresh` invalidates the previous refresh token and issues a new one. Reuse of a revoked token is rejected. This limits the damage window if a refresh token is intercepted.

**Ownership enforcement at the handler level.** Every todo handler explicitly checks `todo.user_id == current_user.id` rather than relying on filtered queries alone. A mismatch returns 403.

**SQLite for tests.** The `get_db` dependency is overridden in `conftest.py` to use an in-memory SQLite database. This makes the test suite self-contained, fast, and free of external dependencies.

**bcrypt cost factor.** Uses the default bcrypt cost factor (12 rounds). This is intentionally slow to resist offline brute-force attacks on the password hash.

**Pydantic v2.** Schemas use `model_config = {"from_attributes": True}` for ORM model serialisation. Field validation (e.g., username lowercasing) happens inside `@field_validator` methods on the schema, not in the route handler.
