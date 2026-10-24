import pytest
from httpx import AsyncClient

TODOS_URL = "/api/v1/todos"


@pytest.fixture
async def todo(client: AsyncClient, auth_headers: dict) -> dict:
    """Create a todo for the default test user and return it."""
    resp = await client.post(
        TODOS_URL,
        json={"title": "Buy milk", "description": "Whole milk", "priority": "low"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# Create


async def test_create_todo_returns_persisted_todo(todo: dict):
    """Assert that a created todo echoes the payload and starts incomplete."""
    assert todo["title"] == "Buy milk"
    assert todo["description"] == "Whole milk"
    assert todo["priority"] == "low"
    assert todo["completed"] is False


async def test_create_todo_applies_defaults(client: AsyncClient, auth_headers: dict):
    """Assert that only the title is required; the other fields get their defaults."""
    resp = await client.post(TODOS_URL, json={"title": "Minimal"}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["description"] is None
    assert body["due_date"] is None
    assert body["priority"] == "medium"


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "x" * 256}, {"title": "Bad priority", "priority": "urgent"}],
    ids=["empty-title", "title-too-long", "unknown-priority"],
)
async def test_create_todo_invalid_payload_returns_422(
    client: AsyncClient, auth_headers: dict, payload: dict
):
    """Assert that payloads violating the schema are rejected."""
    resp = await client.post(TODOS_URL, json=payload, headers=auth_headers)
    assert resp.status_code == 422


# Read


async def test_list_todos_starts_empty(client: AsyncClient, auth_headers: dict):
    """Assert that a new user has no todos."""
    resp = await client.get(TODOS_URL, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_todos_paginates(client: AsyncClient, auth_headers: dict):
    """Assert that limit and offset page through todos without overlap."""
    for i in range(3):
        await client.post(TODOS_URL, json={"title": f"todo {i}"}, headers=auth_headers)

    first = (await client.get(f"{TODOS_URL}?limit=2", headers=auth_headers)).json()
    rest = (await client.get(f"{TODOS_URL}?limit=2&offset=2", headers=auth_headers)).json()
    assert len(first) == 2
    assert len(rest) == 1
    assert {t["id"] for t in first}.isdisjoint(t["id"] for t in rest)


async def test_list_todos_caps_limit_at_100(client: AsyncClient, auth_headers: dict):
    """Assert that a page size above 100 is rejected."""
    resp = await client.get(f"{TODOS_URL}?limit=101", headers=auth_headers)
    assert resp.status_code == 422


async def test_get_todo_returns_todo(client: AsyncClient, auth_headers: dict, todo: dict):
    """Assert that a todo can be fetched by id."""
    resp = await client.get(f"{TODOS_URL}/{todo['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == todo


async def test_get_missing_todo_returns_404(client: AsyncClient, auth_headers: dict):
    """Assert that an unknown id returns 404."""
    resp = await client.get(
        f"{TODOS_URL}/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# Update


async def test_update_todo_changes_only_given_fields(
    client: AsyncClient, auth_headers: dict, todo: dict
):
    """Assert that PATCH updates the supplied fields and leaves the rest untouched."""
    resp = await client.patch(
        f"{TODOS_URL}/{todo['id']}",
        json={"completed": True, "title": "Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is True
    assert body["title"] == "Updated"
    assert body["description"] == todo["description"]


async def test_update_todo_clears_optional_field(
    client: AsyncClient, auth_headers: dict, todo: dict
):
    """Assert that an optional field can be cleared with an explicit null."""
    resp = await client.patch(
        f"{TODOS_URL}/{todo['id']}", json={"description": None}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["description"] is None


async def test_update_todo_rejects_null_required_field(
    client: AsyncClient, auth_headers: dict, todo: dict
):
    """Assert that a required field cannot be cleared with an explicit null."""
    resp = await client.patch(
        f"{TODOS_URL}/{todo['id']}", json={"title": None}, headers=auth_headers
    )
    assert resp.status_code == 422


# Delete


async def test_delete_todo_removes_it(client: AsyncClient, auth_headers: dict, todo: dict):
    """Assert that a deleted todo can no longer be fetched."""
    resp = await client.delete(f"{TODOS_URL}/{todo['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"{TODOS_URL}/{todo['id']}", headers=auth_headers)
    assert resp.status_code == 404


# Authorization


async def test_todos_require_access_token(client: AsyncClient):
    """Assert that the todo endpoints reject unauthenticated requests."""
    resp = await client.get(TODOS_URL)
    assert resp.status_code == 401


async def test_other_users_todo_is_invisible(client: AsyncClient, todo: dict):
    """Assert that another user gets 404 for every operation on someone else's todo."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "username": "userb", "password": "pass1234"},
    )
    login = await client.post(
        "/api/v1/auth/login", data={"username": "userb", "password": "pass1234"}
    )
    headers_b = {"Authorization": f"Bearer {login.json()['access_token']}"}
    url = f"{TODOS_URL}/{todo['id']}"

    assert (await client.get(TODOS_URL, headers=headers_b)).json() == []
    assert (await client.get(url, headers=headers_b)).status_code == 404
    assert (await client.patch(url, json={"title": "Hacked"}, headers=headers_b)).status_code == 404
    assert (await client.delete(url, headers=headers_b)).status_code == 404
