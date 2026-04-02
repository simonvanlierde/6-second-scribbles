"""Database configuration and session management"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Base class for models (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass


# Lazy singletons — created on first use so tests can patch settings before init
_engine = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def _get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


# Convenience accessor for code that imports async_session_maker directly
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return _get_session_maker()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting database sessions."""
    async with _get_session_maker()() as session:
        yield session


async def init_db():
    """Initialize database tables"""
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    global _engine, _session_maker
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
