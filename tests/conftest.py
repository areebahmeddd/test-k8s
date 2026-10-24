import os

# Settings are read at import time, so the test secret must be set before importing the app.
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import get_db
from app.main import app
from app.models.base import Base

USER = {"email": "user@example.com", "username": "testuser", "password": "password123"}


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncGenerator[AsyncEngine]:
    """Create a fresh file-based SQLite database per test, shared by the client and db_session."""
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    """Provide an HTTPX client whose requests use the test database."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db() -> AsyncGenerator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Provide a direct database session for arranging test data."""
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict[str, str]:
    """Register the default test user and return its credentials merged with the profile."""
    resp = await client.post("/api/v1/auth/register", json=USER)
    assert resp.status_code == 201
    return {**USER, **resp.json()}


@pytest.fixture
async def tokens(client: AsyncClient, registered_user: dict[str, str]) -> dict[str, str]:
    """Log in as the default test user and return the token response."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def auth_headers(tokens: dict[str, str]) -> dict[str, str]:
    """Return Authorization headers for the default test user's access token."""
    return {"Authorization": f"Bearer {tokens['access_token']}"}
