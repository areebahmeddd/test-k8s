# Testing Standards (pytest · httpx · AsyncClient)

## Naming Convention

```python
# Pattern: test_<feature>_<scenario>_<expected_result>
def test_create_todo_with_valid_data_returns_201(): ...
def test_create_todo_with_missing_title_returns_422(): ...
def test_get_todo_when_not_found_returns_404(): ...
def test_update_todo_when_not_owner_returns_403(): ...
```

## Test Organization

| Location             | What                                  | Rules                           |
| -------------------- | ------------------------------------- | ------------------------------- |
| `tests/unit/`        | Pure logic, utils, security functions | No I/O, no network, no database |
| `tests/integration/` | Full API request/response cycle       | Test database, real HTTP client |

## Fixtures

```python
from httpx import AsyncClient, ASGITransport
from collections.abc import AsyncGenerator

@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
```

- `asyncio_mode = "auto"` in `pyproject.toml` — no `@pytest.mark.asyncio` needed
- Scope fixtures by cost: `session` → expensive · `module` → medium · default → cheap
- Never share mutable state between tests

## Async Tests

```python
async def test_create_todo_returns_created_resource(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/todos/",
        json={"title": "Buy milk"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
```

## What NOT to Test

- Pydantic field validation that merely mirrors a `Field()` constraint
- FastAPI internals (routing, OpenAPI schema generation)
- Third-party library behavior
- Implementation details — test behavior, not how it's built
