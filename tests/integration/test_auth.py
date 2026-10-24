import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


FAR_FUTURE = datetime(2999, 1, 1, tzinfo=UTC)


def _sign(claims: dict[str, object]) -> str:
    """Sign arbitrary claims with the app secret to craft edge-case tokens."""
    return jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)


async def _deactivate(db_session: AsyncSession, username: str) -> None:
    await db_session.execute(update(User).where(User.username == username).values(is_active=False))
    await db_session.commit()


# Register


async def test_register_returns_profile_without_password_hash(client: AsyncClient):
    """Assert that registration returns 201 and never exposes the password hash."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "username": "NewUser", "password": "pass1234"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["username"] == "newuser"
    assert "hashed_password" not in body


async def test_register_duplicate_returns_409(client: AsyncClient, registered_user: dict):
    """Assert that an already-taken email or username returns 409."""
    resp = await client.post("/api/v1/auth/register", json=registered_user)
    assert resp.status_code == 409


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("bad user!", "pass1234"),  # characters outside [A-Za-z0-9_]
        ("ab", "pass1234"),  # shorter than 3 characters
        ("shortpw", "pass123"),  # shorter than 8 characters
        ("longpw", "é" * 37),  # 74 bytes, over bcrypt's 72-byte limit
    ],
)
async def test_register_invalid_input_returns_422(
    client: AsyncClient, username: str, password: str
):
    """Assert that invalid usernames and passwords are rejected before reaching bcrypt."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "username": username, "password": password},
    )
    assert resp.status_code == 422


# Login


async def test_login_returns_bearer_token_pair(tokens: dict):
    """Assert that valid credentials return an access and refresh token pair."""
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_login_username_is_case_insensitive(client: AsyncClient, registered_user: dict):
    """Assert that usernames are normalized, so login works regardless of case."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "TestUser", "password": registered_user["password"]},
    )
    assert resp.status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [("testuser", "wrongpass"), ("nobody", "password123"), ("testuser", "x" * 100)],
    ids=["wrong-password", "unknown-user", "over-bcrypt-limit"],
)
async def test_login_bad_credentials_returns_401(
    client: AsyncClient, registered_user: dict, username: str, password: str
):
    """Assert that every kind of bad credential gets the same 401, never a 500."""
    resp = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 401


async def test_login_inactive_user_returns_403(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """Assert that a deactivated user cannot log in."""
    await _deactivate(db_session, registered_user["username"])

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert resp.status_code == 403


# Refresh


async def test_refresh_returns_new_token_pair(client: AsyncClient, tokens: dict):
    """Assert that a valid refresh token is exchanged for a new pair."""
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    # The access token may be identical within the same second; the refresh token never is.
    assert resp.json()["refresh_token"] != tokens["refresh_token"]


async def test_refresh_rejects_reused_token(client: AsyncClient, tokens: dict):
    """Assert that a rotated refresh token cannot be replayed."""
    await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401


async def test_refresh_rejects_unknown_token(client: AsyncClient):
    """Assert that an unrecognized refresh token returns 401."""
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


async def test_refresh_rejects_expired_token(
    client: AsyncClient, registered_user: dict, db_session: AsyncSession
):
    """Assert that an expired refresh token returns 401."""
    raw_token = generate_refresh_token()
    db_session.add(
        RefreshToken(
            token_hash=hash_refresh_token(raw_token),
            user_id=uuid.UUID(registered_user["id"]),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await db_session.commit()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
    assert resp.status_code == 401


async def test_refresh_rejects_inactive_user(
    client: AsyncClient, tokens: dict, registered_user: dict, db_session: AsyncSession
):
    """Assert that a deactivated user cannot mint new tokens with an existing refresh token."""
    await _deactivate(db_session, registered_user["username"])

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401


async def test_issuing_tokens_prunes_dead_refresh_tokens(
    client: AsyncClient, tokens: dict, registered_user: dict, db_session: AsyncSession
):
    """Assert that rotated tokens are deleted, leaving one live token per session."""
    refresh_token = tokens["refresh_token"]
    for _ in range(3):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        refresh_token = resp.json()["refresh_token"]

    stored = await db_session.scalars(
        select(RefreshToken).where(RefreshToken.user_id == uuid.UUID(registered_user["id"]))
    )
    assert [t.token_hash for t in stored] == [hash_refresh_token(refresh_token)]


# Logout


async def test_logout_revokes_refresh_token(client: AsyncClient, tokens: dict, auth_headers: dict):
    """Assert that a logged-out refresh token can no longer be used."""
    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth_headers,
    )
    assert resp.status_code == 204

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 401


async def test_logout_unknown_token_is_a_no_op(client: AsyncClient, auth_headers: dict):
    """Assert that logging out an unknown refresh token still returns 204."""
    resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "token-that-does-not-exist"},
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_logout_requires_access_token(client: AsyncClient, tokens: dict):
    """Assert that logout without an access token returns 401."""
    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


# Access tokens on protected routes


async def test_me_returns_current_user(
    client: AsyncClient, registered_user: dict, auth_headers: dict
):
    """Assert that /me returns the profile of the token's user."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == registered_user["username"]


async def test_me_requires_access_token(client: AsyncClient):
    """Assert that /me without a token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        _sign({"sub": str(uuid.uuid4()), "type": "refresh", "exp": FAR_FUTURE}),
        _sign({"type": "access", "exp": FAR_FUTURE}),
        _sign({"sub": "not-a-uuid", "type": "access", "exp": FAR_FUTURE}),
    ],
    ids=["malformed", "wrong-type", "missing-sub", "non-uuid-sub"],
)
async def test_invalid_access_token_returns_401(client: AsyncClient, token: str):
    """Assert that malformed or incorrectly-claimed tokens are rejected."""
    resp = await client.get("/api/v1/auth/me", headers=_bearer(token))
    assert resp.status_code == 401


async def test_access_token_of_inactive_user_returns_401(
    client: AsyncClient, registered_user: dict, auth_headers: dict, db_session: AsyncSession
):
    """Assert that a still-valid token stops working once its user is deactivated."""
    await _deactivate(db_session, registered_user["username"])

    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 401
