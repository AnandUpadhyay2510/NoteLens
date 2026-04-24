"""
Database configuration and session management.

Provides the async SQLAlchemy engine, session factory, and a FastAPI
dependency for injecting database sessions into route handlers.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Create the async engine
# For SQLite, connect_args ensures thread safety
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

# Session factory — produces AsyncSession instances
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    The session is automatically closed after the request completes,
    and any uncommitted changes are rolled back on error.

    Yields:
        AsyncSession: An active database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Create all database tables defined by ORM models.

    This is used during application startup. In production,
    prefer Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """
    Drop all database tables. Use with caution — primarily for testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
