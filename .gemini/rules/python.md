# Python Standards (Python 3.11 · uv · Ruff · Pydantic v2)

## Type Annotations

- Every function parameter and return type must be annotated — no exceptions
- Use `X | Y` union syntax — not `Optional[X]` or `Union[X, Y]`
- Use built-in generics: `list[X]`, `dict[K, V]` — not `List`, `Dict`
- Use `typing.Protocol` for structural subtyping

```python
# Correct
def get_user(user_id: int) -> User | None: ...

# Wrong
def get_user(user_id: int) -> Optional[User]: ...
```

## Async Patterns

- All FastAPI route handlers must be `async def`
- All SQLAlchemy operations must use `AsyncSession` with `await`
- Never use `requests` — use `httpx.AsyncClient`
- Never call blocking I/O inside `async def` — use `asyncio.to_thread()` if unavoidable
- Use `asyncio.gather()` for concurrent independent operations

## Pydantic v2

- `model_config = ConfigDict(from_attributes=True)` on schemas that map to ORM models
- Use `@field_validator` and `@model_validator` (v1 `@validator` is removed)
- Use `model.model_dump()` — `model.dict()` is removed in v2
- Always set `response_model=` on every FastAPI route decorator
- Input constraints via `Field(min_length=1, max_length=255, gt=0)` — not manual `if` checks

## Error Handling

- Raise specific exceptions, never bare `Exception`
- Use `HTTPException` for HTTP errors with a descriptive `detail` string
- Never catch `Exception` broadly without logging and re-raising
- Pydantic validation errors propagate automatically as 422 — don't intercept them

## Logging

- No `print()` — use `structlog` (this project) or `logging.getLogger(__name__)`
- Never log sensitive data: passwords, tokens, full request bodies with PII
- Levels: `DEBUG` for tracing · `INFO` for events · `WARNING` for recoverable · `ERROR` for failures

## Ruff Compliance

- Run before committing: `uv run ruff check app/ --fix` then `uv run ruff format app/`
- No wildcard imports (`from module import *`)
- Remove unused imports immediately — no `# noqa` without reason
- Import order: stdlib → third-party → local (Ruff enforces automatically)
