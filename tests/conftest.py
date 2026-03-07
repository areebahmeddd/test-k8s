import pytest
from httpx import AsyncClient, ASGITransport
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.base import Base

_USER = {"email": "user@example.com", "username": "testuser", "password": "password123"}


@pytest.fixture
async def engine(tmp_path):
    """Create a fresh file-based SQLite engine per test so direct DB access and the HTTP client share the same data."""
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def client(engine):
    """Provide an HTTPX test client backed by the test-scoped SQLite database."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db():
        """Yield a session from the test-scoped database."""
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a direct database session for test data setup and manipulation."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register the default test user and return its credentials merged with the profile response."""
    resp = await client.post("/api/v1/auth/register", json=_USER)
    assert resp.status_code == 201
    return {**_USER, **resp.json()}


@pytest.fixture
async def tokens(client: AsyncClient, registered_user: dict) -> dict:
    """Log in as the default test user and return the token response dict."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def auth_headers(tokens: dict) -> dict:
    """Return Authorization headers for the default test user's access token."""
    return {"Authorization": f"Bearer {tokens['access_token']}"}
