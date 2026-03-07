import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def test_register_success(client: AsyncClient):
    """Assert that a valid registration request creates a user and returns 201 without sensitive fields."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "pass1234",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["username"] == "newuser"
    assert "hashed_password" not in body


async def test_register_duplicate_raises_conflict(
    client: AsyncClient, registered_user: dict
):
    """Assert that registering with an already-taken email or username returns 409."""
    resp = await client.post("/api/v1/auth/register", json=registered_user)
    assert resp.status_code == 409


async def test_register_invalid_username(client: AsyncClient):
    """Assert that a username containing non-alphanumeric characters returns 422."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@example.com",
            "username": "bad user!",
            "password": "pass1234",
        },
    )
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient, registered_user: dict):
    """Assert that valid credentials return a 200 response containing a bearer token pair."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, registered_user: dict):
    """Assert that an incorrect password causes the login endpoint to return 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["username"], "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    """Assert that logging in with a non-existent username returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "pass"},
    )
    assert resp.status_code == 401


async def test_login_inactive_user(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """Assert that a deactivated user cannot log in and receives 403."""
    await db_session.execute(
        update(User)
        .where(User.username == registered_user["username"])
        .values(is_active=False)
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 403


async def test_refresh_returns_new_tokens(client: AsyncClient, tokens: dict):
    """Assert that a valid refresh token exchange returns 200 with a new refresh token."""
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert "access_token" in new_tokens
    # refresh token is always a new UUID4 — access token may be identical within the same second
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


async def test_refresh_token_rotation_revokes_old(client: AsyncClient, tokens: dict):
    """Assert that a consumed refresh token cannot be reused after rotation (replay prevention)."""
    # First refresh succeeds and revokes the original token
    await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    # Reusing the original token must fail
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient):
    """Assert that submitting an unrecognised refresh token value returns 401."""
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )
    assert resp.status_code == 401


async def test_refresh_expired_token(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """Assert that an expired refresh token is rejected with 401."""
    raw_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db_session.add(
        RefreshToken(
            token_hash=token_hash,
            user_id=uuid.UUID(registered_user["id"]),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await db_session.commit()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(
    client: AsyncClient, tokens: dict, auth_headers: dict
):
    """Assert that logout revokes the refresh token so it cannot be reused."""
    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # The refresh token must now be rejected
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401


async def test_logout_unauthenticated(client: AsyncClient, tokens: dict):
    """Assert that the logout endpoint requires a valid access token."""
    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401


async def test_logout_idempotent(client: AsyncClient, auth_headers: dict):
    """Assert that logging out with an unknown refresh token returns 204 without error."""
    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "token-that-does-not-exist"},
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_me_returns_current_user(
    client: AsyncClient, registered_user: dict, auth_headers: dict
):
    """Assert that /me returns the authenticated user's profile for a valid token."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == registered_user["username"]


async def test_me_unauthenticated(client: AsyncClient):
    """Assert that accessing /me without a token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_protected_route_wrong_token_type(client: AsyncClient):
    """Assert that a token whose type claim is not 'access' is rejected by protected routes."""
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "refresh",
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_protected_route_missing_sub(client: AsyncClient):
    """Assert that a token with no sub claim is rejected by protected routes."""
    token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(minutes=30), "type": "access"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_protected_route_invalid_uuid_sub(client: AsyncClient):
    """Assert that a token whose sub claim is not a valid UUID is rejected."""
    token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "type": "access",
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_protected_route_malformed_token(client: AsyncClient):
    """Assert that a syntactically invalid bearer token is rejected with 401."""
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid-jwt-string"}
    )
    assert resp.status_code == 401


async def test_protected_route_inactive_user(
    client: AsyncClient,
    registered_user: dict,
    auth_headers: dict,
    db_session: AsyncSession,
):
    """Assert that a valid token for a now-inactive user is rejected with 401."""
    await db_session.execute(
        update(User)
        .where(User.username == registered_user["username"])
        .values(is_active=False)
    )
    await db_session.commit()

    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 401
