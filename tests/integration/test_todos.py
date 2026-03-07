from httpx import AsyncClient

_TODO_PAYLOAD = {"title": "Buy milk", "description": "Whole milk", "priority": "low"}


async def test_list_todos_empty(client: AsyncClient, auth_headers: dict):
    """Assert that a newly registered user starts with an empty todo list."""
    resp = await client.get("/api/v1/todos", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_todo(client: AsyncClient, auth_headers: dict):
    """Assert that POSTing a valid payload creates a todo and returns 201 with the persisted data."""
    resp = await client.post("/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == _TODO_PAYLOAD["title"]
    assert body["completed"] is False
    assert "id" in body


async def test_create_todo_without_description(client: AsyncClient, auth_headers: dict):
    """Assert that description is optional and omitting it still creates a todo successfully."""
    resp = await client.post(
        "/api/v1/todos", json={"title": "No description"}, headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["description"] is None


async def test_create_todo_invalid_priority(client: AsyncClient, auth_headers: dict):
    """Assert that an unrecognised priority value returns 422."""
    resp = await client.post(
        "/api/v1/todos",
        json={"title": "Bad priority", "priority": "urgent"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_list_todos_returns_created(client: AsyncClient, auth_headers: dict):
    """Assert that a created todo appears in the subsequent list response."""
    await client.post("/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers)
    resp = await client.get("/api/v1/todos", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_todo(client: AsyncClient, auth_headers: dict):
    """Assert that a created todo can be fetched by its ID and returns the correct data."""
    create_resp = await client.post(
        "/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers
    )
    todo_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id


async def test_get_todo_not_found(client: AsyncClient, auth_headers: dict):
    """Assert that requesting a non-existent todo UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/todos/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_todo(client: AsyncClient, auth_headers: dict):
    """Assert that PATCHing a todo updates only the supplied fields and returns the new state."""
    todo_id = (
        await client.post("/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers)
    ).json()["id"]

    resp = await client.patch(
        f"/api/v1/todos/{todo_id}",
        json={"completed": True, "title": "Updated title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is True
    assert body["title"] == "Updated title"


async def test_delete_todo(client: AsyncClient, auth_headers: dict):
    """Assert that DELETEing a todo returns 204 and the item is no longer retrievable."""
    todo_id = (
        await client.post("/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers)
    ).json()["id"]

    assert (
        await client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    ).status_code == 204
    assert (
        await client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    ).status_code == 404


async def test_todo_ownership_enforced(client: AsyncClient, auth_headers: dict):
    """Assert that a second user cannot read, update, or delete another user's todo."""
    # Create a todo as user A
    todo_id = (
        await client.post("/api/v1/todos", json=_TODO_PAYLOAD, headers=auth_headers)
    ).json()["id"]

    # Register and log in as user B
    await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "username": "userB", "password": "pass1234"},
    )
    token_b = (
        await client.post(
            "/api/v1/auth/login", data={"username": "userb", "password": "pass1234"}
        )
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B cannot read, update, or delete user A's todo
    assert (
        await client.get(f"/api/v1/todos/{todo_id}", headers=headers_b)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/todos/{todo_id}", json={"title": "Hacked"}, headers=headers_b
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/todos/{todo_id}", headers=headers_b)
    ).status_code == 404


async def test_todos_unauthenticated(client: AsyncClient):
    """Assert that accessing the todos endpoint without authentication returns 401."""
    resp = await client.get("/api/v1/todos")
    assert resp.status_code == 401
