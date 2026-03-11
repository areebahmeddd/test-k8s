---
paths:
  - "**/*.py"
---

# Python Standards (Python 3.11 · uv · Ruff · Pydantic v2)

## Type Annotations

- Every function parameter and return type must be annotated — no exceptions
- Use `X | Y` union syntax, **not** `Optional[X]` or `Union[X, Y]`
- Use built-in generics: `list[X]`, `dict[K, V]`, `tuple[X, ...]` — not `List`, `Dict`, `Tuple`
- Use `typing.Protocol` for structural subtyping (not ABCs for duck-typed interfaces)
- `ClassVar[T]` for class-level attributes that are not instance attributes

```python
# Correct
def get_user(user_id: int) -> User | None: ...
def process(items: list[str]) -> dict[str, int]: ...

# Wrong
def get_user(user_id: int) -> Optional[User]: ...
def process(items: List[str]) -> Dict[str, int]: ...
```

## Async Patterns

- All FastAPI route handlers must be `async def`
- All SQLAlchemy operations must use `AsyncSession` with `await`
- Never use `requests` — use `httpx.AsyncClient`
- Never call blocking I/O inside an `async def` — use `asyncio.to_thread()` if unavoidable
- Use `asyncio.gather()` for concurrent independent operations (not sequential `await`)
- Fire-and-forget `asyncio.create_task()` must have error logging (task errors are silently dropped)

## Pydantic v2

- `model_config = ConfigDict(from_attributes=True)` on schemas that map to ORM models
- Validators: use `@field_validator` and `@model_validator` (v1 `@validator` is removed)
- Serialization: use `model.model_dump()` — `model.dict()` is removed in v2
- Always set `response_model=` on every FastAPI route decorator
- Input validation constraints via `Field(min_length=1, max_length=255, gt=0)` — not manual `if` checks

## Error Handling

- Raise specific exceptions, never bare `Exception`
- Use `HTTPException` for HTTP errors with a descriptive `detail` string
- Never catch `Exception` broadly without logging and re-raising
- Pydantic validation errors propagate automatically as 422 — don't intercept them
- No silent swallowing: `except SomeError: pass` is always wrong

## Logging

- No `print()` — use `structlog` (this project) or `logging.getLogger(__name__)`
- Never log sensitive data: passwords, tokens, full request bodies with PII
- Log at the right level: `DEBUG` for tracing, `INFO` for normal events, `WARNING` for recoverable issues, `ERROR` for failures

## Comments

- Prefer self-documenting code — if a comment is needed to explain *what* the code does, rename or refactor instead
- Comment only to explain *why*: a non-obvious decision, constraint, or trade-off
- Use imperative mood, no subject: `# Retry on 503` not `# This retries on 503` or `# We retry on 503`
- No AI phrasing: avoid "Note that", "It's important to", "This function handles", "We need to"
- Zero comments is better than a weak or obvious one

## Project Structure

- `app/models/` — SQLAlchemy ORM models only (no logic, no validation)
- `app/schemas/` — Pydantic schemas only (one file per domain area)
- `app/api/v1/` — FastAPI route handlers (thin — validate input, call service, return response)
- `app/core/` — Config, database engine, security, telemetry

## Ruff Compliance

- Run before committing: `uv run ruff check app/ --fix` then `uv run ruff format app/`
- No `# type: ignore` without an explanatory comment on the same line
- No wildcard imports (`from module import *`)
- Remove unused imports immediately — do not leave them with `# noqa`
- Import order: standard library → third-party → local (Ruff enforces this automatically)
