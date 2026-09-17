import os
import tempfile
from collections.abc import AsyncGenerator

# Settings are cached, so the test environment must be set before any app import.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENABLE_DEMO_ROUTES", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-long-enough-for-tests-123")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-that-is-long-enough-abc123")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:1/0")
os.environ.setdefault("STORAGE_LOCAL_PATH", tempfile.mkdtemp(prefix="novaa-test-"))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import session as session_module
from app.db.base import Base
from app.db.session import get_db
from app.domain import models  # noqa: F401  (registers the mappers)
from app.main import app


@pytest_asyncio.fixture
async def engine():
    # StaticPool keeps the in-memory database alive across connections.
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Jobs that own their session resolve it through db.session.new_session, so
    # one patch points every background path at the same in-memory database.
    monkeypatch.setattr(session_module, "async_session", maker)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client) -> AsyncGenerator[AsyncClient, None]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "mobile": "9876543210",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    yield client


@pytest.fixture
def anyio_backend():
    return "asyncio"
