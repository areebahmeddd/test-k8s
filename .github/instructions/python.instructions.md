---
name: Python
description: Python conventions for the FastAPI app, migrations, tests and the Pulumi program.
applyTo: "**/*.py"
---

# Python

- Target Python 3.14; Ruff (`pyproject.toml`) is the formatter and linter, so don't hand-format.
- Annotate every signature. Use `X | None`, built-in generics (`list[str]`) and `collections.abc` (`AsyncGenerator[T]`).
- Everything on the request path is async: `AsyncSession` queries are always awaited; never call blocking I/O in `async def`.
- Pydantic v2 only: `ConfigDict(from_attributes=True)`, `Field(...)` constraints, `@field_validator`, `model_dump()`.
- SQLAlchemy 2.0 typed ORM: `Mapped[...]` + `mapped_column(...)`, `select()` statements, no legacy `Query` API.
- Read configuration through `app.core.config.settings`; `SecretStr` values are unwrapped only where used.
- Log via `logging.getLogger(__name__)`; pass context with `extra={...}`. No `print()`, no secrets in logs.
- Raise specific exceptions; never swallow errors with a bare `except`/`pass`.
- Comments explain _why_, not _what_. Docstrings are one imperative sentence unless more is genuinely needed.
