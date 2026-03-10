---
name: Testing Standards
description: "Use when writing tests, reviewing test coverage, designing test fixtures, fixing flaky tests, deciding what to test, or structuring pytest suites. Covers test naming, async testing, fixture design, parametrize patterns, integration vs unit split, and what NOT to test. Triggers on: write a test, test this function, how do I test, improve test coverage, fix flaky test, add integration test, unit test."
---

# Testing Standards (pytest · httpx · AsyncClient)

## Test Naming Convention

```python
# Pattern: test_<feature>_<scenario>_<expected_result>
def test_create_todo_with_valid_data_returns_201(): ...
def test_create_todo_with_missing_title_returns_422(): ...
def test_get_todo_when_not_found_returns_404(): ...
def test_update_todo_when_not_owner_returns_403(): ...
```

The name should read as a specification: "Given X, when Y, then Z."

## Test Organization

| Where                | What                                        | Rules                                |
| -------------------- | ------------------------------------------- | ------------------------------------ |
| `tests/unit/`        | Pure logic, utils, security functions       | No I/O, no network, no database      |
| `tests/integration/` | API endpoints (full request/response cycle) | Uses test database, real HTTP client |

Never mix concerns: a "unit" test that requires a database is an integration test.

## Fixtures

```python
# Use yield for teardown — clean and explicit
@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

# Scope by cost
@pytest.fixture(scope="session")   # database setup — expensive
@pytest.fixture(scope="module")    # schema setup — medium cost
@pytest.fixture                    # default function scope — cheap, isolated
```

- Fixtures compose: `authenticated_client(client, test_user)` is clean
- Never share mutable state between tests — tests must be order-independent
- Use `conftest.py` for shared fixtures; keep test-file-specific fixtures in the test file

## Async Tests

```python
@pytest.mark.asyncio
async def test_create_todo_returns_created_resource(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/todos/",
        json={"title": "Buy milk", "description": None},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Buy milk"
    assert data["completed"] is False
    assert "id" in data
```

## Assertions

- Assert the **contract** (response shape, status code, state change), not the implementation
- One logical concern per test — don't chain multiple unrelated assertions
- Use specific assertions: `assert response.status_code == 201` not `assert response.ok`
- Test the 404/422/403 paths as deliberately as the happy path

## Parametrize Repetitive Cases

```python
@pytest.mark.parametrize("title,expected_status", [
    ("Buy milk", 201),           # valid
    ("", 422),                    # too short
    ("a" * 300, 422),             # too long
    ("   ", 422),                 # whitespace only
])
@pytest.mark.asyncio
async def test_create_todo_title_validation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    title: str,
    expected_status: int,
) -> None:
    response = await client.post(
        "/api/v1/todos/",
        json={"title": title},
        headers=auth_headers,
    )
    assert response.status_code == expected_status
```

## What to Test (Coverage That Matters)

✅ Test these:

- All API endpoints: happy path AND error paths (401, 403, 404, 422)
- Business rule enforcement (ownership, permissions, state transitions)
- Input validation boundaries (empty, max length, invalid format)
- Security: authenticated endpoints reject unauthenticated requests

❌ Don't test these:

- Pydantic's built-in validation logic (trust the library)
- SQLAlchemy's query building (trust the ORM)
- FastAPI's request parsing (trust the framework)
- Implementation details that will change during refactoring

## Anti-Patterns

| Anti-pattern                             | Fix                                               |
| ---------------------------------------- | ------------------------------------------------- |
| `time.sleep()` in tests                  | Use `asyncio.sleep(0)` or mock time               |
| Real HTTP calls to external APIs         | Mock with `httpx.MockTransport` or `respx`        |
| Database state shared between tests      | Use transaction rollback per test or re-create DB |
| Tests that pass only in a specific order | Make each test self-contained with fixtures       |
| Testing `model.dict()` output            | Test the API response, not the internal model     |
