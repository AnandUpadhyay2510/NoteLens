"""
Pytest configuration and shared fixtures.

Provides a test database (in-memory SQLite), test client, and
helper fixtures for creating authenticated users and sample documents.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Test database setup (in-memory SQLite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the database dependency with the test database."""
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Event loop fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database lifecycle fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and return a test student user."""
    user = User(
        email="student@test.edu",
        username="teststudent",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_educator(db_session: AsyncSession) -> User:
    """Create and return a test educator user."""
    user = User(
        email="educator@test.edu",
        username="testeducator",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.EDUCATOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create and return a test admin user."""
    user = User(
        email="admin@test.edu",
        username="testadmin",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Return Authorization headers with a valid JWT for the test user."""
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def educator_headers(test_educator: User) -> dict:
    """Return Authorization headers for the test educator."""
    token = create_access_token(data={"sub": test_educator.id})
    return {"Authorization": f"Bearer {token}"}
