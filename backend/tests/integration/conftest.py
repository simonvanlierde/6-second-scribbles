"""Real Postgres/Redis fixtures for backend integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.postgres import PostgresContainer

import app.main as main_module
from app.core import database
from app.core import redis as redis_module
from app.core.config import settings
from app.core.migrations import run_migrations
from scripts import seed_data

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncConnection

fastapi_app = main_module.application

_POSTGRES_PASSWORD = uuid4().hex


def _postgres_host_port(container: PostgresContainer) -> tuple[str, int]:
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(5432))
    return host, port


@dataclass
class RedisTestContainer:
    """Small Redis container wrapper using structured wait strategies."""

    image: str = "redis:7-alpine"
    port: int = 6379

    def __post_init__(self) -> None:
        self._container = DockerContainer(self.image)
        self._container.with_exposed_ports(self.port)
        self._container.waiting_for(LogMessageWaitStrategy("Ready to accept connections"))

    def __enter__(self) -> Self:
        self._container.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._container.stop()

    def get_container_host_ip(self) -> str:
        """Return the host IP that exposes this Redis container."""
        return self._container.get_container_host_ip()

    def get_exposed_port(self, port: int) -> int:
        """Return the mapped host port for the requested container port."""
        return self._container.get_exposed_port(port)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Session-scoped Postgres container for integration coverage."""
    with PostgresContainer(
        image="postgres:16-alpine",
        username="postgres",
        password=_POSTGRES_PASSWORD,
        dbname="scribbles_test",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisTestContainer]:
    """Session-scoped Redis container for integration coverage."""
    with RedisTestContainer() as container:
        yield container


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def configure_integration_settings(
    postgres_container: PostgresContainer,
    redis_container: RedisTestContainer,
) -> AsyncGenerator[None]:
    """Point the app at the session-scoped Postgres and Redis containers."""
    await database.close_db()
    await redis_module.close_redis()

    previous = {
        "postgres_host": settings.postgres_host,
        "postgres_port": settings.postgres_port,
        "postgres_password": settings.postgres_password,
        "postgres_db": settings.postgres_db,
        "redis_host": settings.redis_host,
        "redis_port": settings.redis_port,
    }

    pg_host, pg_port = _postgres_host_port(postgres_container)
    settings.postgres_host = pg_host
    settings.postgres_port = pg_port
    settings.postgres_password = SecretStr(_POSTGRES_PASSWORD)
    settings.postgres_db = "scribbles_test"

    settings.redis_host = redis_container.get_container_host_ip()
    settings.redis_port = int(redis_container.get_exposed_port(6379))

    await run_migrations()
    await database.close_db()
    await redis_module.close_redis()
    yield

    await database.close_db()
    await redis_module.close_redis()
    for key, value in previous.items():
        setattr(settings, key, value)


@pytest_asyncio.fixture(loop_scope="session")
async def redis_client() -> AsyncGenerator[Redis]:
    """Clean Redis state before and after each integration test."""
    client = await redis_module.get_redis()
    await client.flushdb()
    yield client
    await client.flushdb()


@pytest_asyncio.fixture(loop_scope="session")
async def db_connection() -> AsyncGenerator[AsyncConnection]:
    """Open a transaction-scoped connection for direct DB integration tests."""
    session_maker = database.get_session_maker()
    engine = session_maker.kw["bind"]
    assert isinstance(engine, AsyncEngine)

    connection = await engine.connect()
    transaction = await connection.begin()
    try:
        yield connection
    finally:
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def db_session_maker(db_connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Sessionmaker bound to the test transaction connection."""
    return async_sessionmaker(
        bind=db_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(
    db_session_maker: async_sessionmaker[AsyncSession],
    redis_client: Redis,
) -> AsyncGenerator[AsyncSession]:
    """Transactional async session for direct DB integration tests."""
    _ = redis_client
    async with db_session_maker() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def async_client(
    db_session_maker: async_sessionmaker[AsyncSession],
    redis_client: Redis,
) -> AsyncGenerator[AsyncClient]:
    """Async client wired to the transactional test database session."""
    _ = redis_client

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        async with db_session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[database.get_async_session] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def seed_data_session_maker(
    monkeypatch: pytest.MonkeyPatch,
    db_session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Route the seed-data script through the transactional test sessionmaker."""
    monkeypatch.setattr(seed_data, "get_session_maker", lambda: db_session_maker)
