"""Database configuration and session management."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# Base class for models (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass


# Lazy singletons so tests can patch settings before initialization.
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    return _get_session_maker()


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session for FastAPI dependencies."""
    async with _get_session_maker()() as session:
        yield session


get_db = get_async_session
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def init_db() -> None:
    """Initialize database tables."""
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_maker
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
