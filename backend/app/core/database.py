"""Database configuration and session management."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class _DatabaseState:
    """Holds lazily created database resources."""

    engine: AsyncEngine | None = None
    session_maker: async_sessionmaker[AsyncSession] | None = None


_state = _DatabaseState()


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
    if _state.engine is None:
        _state.engine = _create_engine()
    return _state.engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _state.session_maker is None:
        _state.session_maker = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _state.session_maker


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
    if _state.engine:
        await _state.engine.dispose()
    _state.engine = None
    _state.session_maker = None
