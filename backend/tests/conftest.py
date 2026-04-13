"""Shared test fixtures and configuration.

Default tests run against in-memory fakes for the database and Redis so unit and
app tests stay fast and deterministic. Container-backed dependencies should be
reserved for explicitly marked integration coverage.
"""
# spell-checker: ignore ASGI, getfixturevalue

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.operators import eq, in_op, is_
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import app.main as main_module
from app.categories.models import Category, CategoryPrompt, Prompt
from app.core import database
from app.core import redis as redis_module
from app.core.config import settings
from app.core.migrations import run_migrations
from app.rooms.manager import GameRoom, RoomManager
from app.rooms.manager import room_manager as global_room_manager
from app.users.models import User

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator, Iterable

    from fastapi import WebSocket
    from sqlalchemy.ext.asyncio import AsyncSession


def _is_integration_test(request: pytest.FixtureRequest) -> bool:
    return request.node.get_closest_marker("integration") is not None


def _postgres_host_port(container: PostgresContainer) -> tuple[str, int]:
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(5432))
    return host, port


def _redis_host_port(container: RedisContainer) -> tuple[str, int]:
    host = container.get_container_host_ip()
    port = int(container.get_exposed_port(6379))
    return host, port


_POSTGRES_PASSWORD = uuid4().hex


async def _reset_real_infra() -> None:
    await database.close_db()
    await redis_module.close_redis()

    await run_migrations()

    table_names = ", ".join(table.name for table in reversed(database.Base.metadata.sorted_tables))
    if table_names:
        async with database._get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))

    redis_client = await redis_module.get_redis()
    await redis_client.flushdb()
    await redis_module.close_redis()
    await database.close_db()


@dataclass
class _FakeDatabaseStore:
    categories: dict[int, Category] = field(default_factory=dict)
    prompts: dict[int, Prompt] = field(default_factory=dict)
    category_prompts: dict[int, CategoryPrompt] = field(default_factory=dict)
    users: dict[str, User] = field(default_factory=dict)
    next_category_id: int = 1
    next_prompt_id: int = 1
    next_category_prompt_id: int = 1


@dataclass
class TestWebSocket:
    """Lean websocket test double for GameRoom unit tests."""

    sent_texts: list[str] = field(default_factory=list)
    close_calls: list[dict[str, Any]] = field(default_factory=list)
    send_error: Exception | None = None

    async def send_text(self, message: str) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent_texts.append(message)

    async def send_json(self, data: object) -> None:
        await self.send_text(json.dumps(data))

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.close_calls.append({"code": code, "reason": reason})


def as_websocket(test_websocket: TestWebSocket) -> WebSocket:
    """Cast a lightweight websocket double to the FastAPI websocket type used by GameRoom."""
    return cast("WebSocket", test_websocket)


class _FakeScalarResult:
    def __init__(self, items: list[Any]):
        self._items = items

    def all(self) -> list[Any]:
        return list(self._items)


class _FakeResult:
    def __init__(
        self,
        items: list[Any] | None = None,
        *,
        rowcount: int | None = None,
        rows: list[tuple[Any, ...]] | None = None,
    ):
        self._items = items or []
        self.rowcount = rowcount
        self._rows = rows or []

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._items)

    def scalar_one_or_none(self) -> Any | None:
        if self._rows:
            first = self._rows[0] if self._rows else None
            if first is None:
                return None
            return first[0] if first else None
        if not self._items:
            return None
        return self._items[0]

    def all(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class FakeAsyncSession:
    def __init__(self, store: _FakeDatabaseStore):
        self._store = store

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def add(self, obj: Any) -> None:
        if isinstance(obj, Category):
            if obj.id is None:
                obj.id = self._store.next_category_id
                self._store.next_category_id += 1
            self._store.categories[obj.id] = obj
            return

        if isinstance(obj, Prompt):
            if obj.id is None:
                obj.id = self._store.next_prompt_id
                self._store.next_prompt_id += 1
            self._store.prompts[obj.id] = obj
            return

        if isinstance(obj, CategoryPrompt):
            if obj.id is None:
                obj.id = self._store.next_category_prompt_id
                self._store.next_category_prompt_id += 1
            obj.category = self._store.categories.get(obj.category_id)
            obj.prompt = self._store.prompts.get(obj.prompt_id)
            self._store.category_prompts[obj.id] = obj
            return

        if isinstance(obj, User):
            self._store.users[obj.id] = obj
            return

        msg = f"Unsupported object type: {type(obj)!r}"
        raise TypeError(msg)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def delete(self, obj: Any) -> None:
        if isinstance(obj, Category):
            self._store.categories.pop(obj.id, None)
            for category_prompt_id, category_prompt in list(self._store.category_prompts.items()):
                if category_prompt.category_id == obj.id:
                    del self._store.category_prompts[category_prompt_id]
            return

        if isinstance(obj, Prompt):
            self._store.prompts.pop(obj.id, None)
            for category_prompt_id, category_prompt in list(self._store.category_prompts.items()):
                if category_prompt.prompt_id == obj.id:
                    del self._store.category_prompts[category_prompt_id]
            return

        if isinstance(obj, CategoryPrompt):
            self._store.category_prompts.pop(obj.id, None)
            return

        if isinstance(obj, User):
            self._store.users.pop(obj.id, None)
            return

        msg = f"Unsupported object type: {type(obj)!r}"
        raise TypeError(msg)

    def expire_all(self) -> None:
        return None

    async def get(self, model: type[Any], primary_key: int) -> Any | None:
        if model is Category:
            return self._store.categories.get(primary_key)
        if model is Prompt:
            return self._store.prompts.get(primary_key)
        if model is CategoryPrompt:
            return self._store.category_prompts.get(primary_key)
        if model is User:
            return self._store.users.get(primary_key)
        msg = f"Unsupported model type: {model!r}"
        raise TypeError(msg)

    async def execute(self, statement) -> _FakeResult:
        if statement.__class__.__name__ == "Select":
            first_description = statement.column_descriptions[0]
            model = first_description["entity"]
            if model is None or first_description.get("expr") is not model:
                rows = self._rows_for_columns(statement)
                return _FakeResult(rows=rows)
            items = list(self._items_for_model(model))
            for criterion in statement._where_criteria:
                items = [item for item in items if _matches(item, criterion)]
            return _FakeResult(items)

        if statement.__class__.__name__ == "Delete":
            table_name = statement.table.name
            target_map: dict[Any, Any]
            if table_name == Category.__tablename__:
                target_map = self._store.categories
            elif table_name == Prompt.__tablename__:
                target_map = self._store.prompts
            elif table_name == CategoryPrompt.__tablename__:
                target_map = self._store.category_prompts
            elif table_name == User.__tablename__:
                target_map = self._store.users
            else:
                msg = f"Unsupported delete table: {table_name}"
                raise TypeError(msg)

            instances = list(target_map.values())
            for criterion in statement._where_criteria:
                instances = [instance for instance in instances if _matches(instance, criterion)]

            deleted = 0
            for instance in instances:
                await self.delete(instance)
                deleted += 1
            return _FakeResult(rowcount=deleted)

        msg = f"Unsupported statement type: {statement.__class__.__name__}"
        raise TypeError(msg)

    def _items_for_model(self, model: type[Any]) -> Iterable[Any]:
        if model is Category:
            return self._store.categories.values()
        if model is Prompt:
            return self._store.prompts.values()
        if model is CategoryPrompt:
            return self._store.category_prompts.values()
        if model is User:
            return self._store.users.values()
        msg = f"Unsupported model type: {model!r}"
        raise TypeError(msg)

    def _rows_for_columns(self, statement) -> list[tuple[Any, ...]]:
        columns = list(statement.selected_columns)
        if not columns:
            return []

        model = getattr(columns[0], "table", None)
        table_name = getattr(model, "name", None)
        if table_name == Category.__tablename__:
            items = list(self._store.categories.values())
        elif table_name == Prompt.__tablename__:
            items = list(self._store.prompts.values())
        elif table_name == CategoryPrompt.__tablename__:
            items = list(self._store.category_prompts.values())
        elif table_name == User.__tablename__:
            items = list(self._store.users.values())
        else:
            return []

        for criterion in statement._where_criteria:
            items = [item for item in items if _matches(item, criterion)]

        rows: list[tuple[Any, ...]] = []
        for item in items:
            rows.append(tuple(getattr(item, column.key) for column in columns))
        return rows


class _FakeSessionMaker:
    def __init__(self, store: _FakeDatabaseStore):
        self._store = store

    def __call__(self) -> FakeAsyncSession:
        return FakeAsyncSession(self._store)


def _matches(instance: Any, criterion: Any) -> bool:
    if isinstance(criterion, BooleanClauseList):
        return all(_matches(instance, clause) for clause in criterion.clauses)

    if isinstance(criterion, BinaryExpression):
        left = criterion.left
        column_name = getattr(left, "key", None)
        if column_name is None:
            column_name = getattr(left, "name", None)
        if column_name is None and hasattr(left, "clause"):
            column_name = getattr(left.clause, "key", None)
        if column_name is None:
            msg = f"Unsupported criterion column: {criterion.left!r}"
            raise TypeError(msg)

        actual = getattr(instance, column_name)
        expected = _extract_value(criterion.right)
        operator_name = getattr(criterion.operator, "__name__", "")

        if criterion.operator is eq or operator_name == "eq":
            return actual == expected
        if criterion.operator is is_ or operator_name == "is_":
            return actual is expected
        if criterion.operator is in_op or operator_name == "in_op":
            return actual in expected
        if operator_name in {"contains_op", "contains"}:
            if isinstance(actual, list):
                if isinstance(expected, list):
                    return all(item in actual for item in expected)
                return expected in actual
            return expected in actual
        if getattr(criterion.operator, "opstring", None) == "@>":
            if isinstance(actual, list):
                if isinstance(expected, list):
                    return all(item in actual for item in expected)
                return expected in actual
            return False

    msg = f"Unsupported criterion: {criterion!r}"
    raise TypeError(msg)


def _extract_value(value: Any) -> Any:
    if value.__class__.__name__ == "Null":
        return None
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "effective_value"):
        return value.effective_value
    return value


@pytest.fixture
def fake_db_store() -> _FakeDatabaseStore:
    return _FakeDatabaseStore()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis(decode_responses=True)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    with PostgresContainer(
        image="postgres:16-alpine",
        username="postgres",
        password=_POSTGRES_PASSWORD,
        dbname="scribbles_test",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    with RedisContainer(image="redis:7-alpine") as container:
        yield container


@pytest.fixture(autouse=True)
async def configure_test_services(
    request: pytest.FixtureRequest,
    monkeypatch,
    fake_db_store: _FakeDatabaseStore,
    fake_redis: FakeRedis,
):
    if _is_integration_test(request):
        postgres = request.getfixturevalue("postgres_container")
        redis_container = request.getfixturevalue("redis_container")

        pg_host, pg_port = _postgres_host_port(postgres)
        monkeypatch.setattr(settings, "postgres_host", pg_host)
        monkeypatch.setattr(settings, "postgres_port", pg_port)
        monkeypatch.setattr(settings, "postgres_password", SecretStr(_POSTGRES_PASSWORD))
        monkeypatch.setattr(settings, "postgres_db", "scribbles_test")

        redis_host, redis_port = _redis_host_port(redis_container)
        monkeypatch.setattr(settings, "redis_host", redis_host)
        monkeypatch.setattr(settings, "redis_port", redis_port)

        redis_module._state.client = None

        main_module.app.dependency_overrides.clear()

        await _reset_real_infra()
        yield
        main_module.app.dependency_overrides.clear()
        redis_module._state.client = None
        await database.close_db()
        await redis_module.close_redis()
        return

    session_maker = _FakeSessionMaker(fake_db_store)

    async def override_get_db() -> AsyncGenerator[FakeAsyncSession]:
        yield FakeAsyncSession(fake_db_store)

    async def fake_close_db() -> None:
        return None

    monkeypatch.setattr(database, "get_session_maker", lambda: session_maker)
    monkeypatch.setattr(database, "_get_session_maker", lambda: session_maker)
    monkeypatch.setattr(database, "close_db", fake_close_db)

    monkeypatch.setattr(redis_module._state, "client", fake_redis)
    monkeypatch.setattr(main_module, "close_db", fake_close_db)

    main_module.app.dependency_overrides[database.get_async_session] = override_get_db
    yield
    main_module.app.dependency_overrides.clear()
    await fake_redis.aclose()


@pytest.fixture(autouse=True)
async def reset_room_manager(configure_test_services) -> AsyncGenerator[None]:
    _ = configure_test_services
    await global_room_manager.stop()
    global_room_manager.rooms.clear()
    yield
    await global_room_manager.stop()
    global_room_manager.rooms.clear()


@pytest.fixture
def test_client() -> Generator[TestClient]:
    """Synchronous test client for FastAPI app using in-memory fakes."""
    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Async test client for FastAPI app using in-memory fakes."""
    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client:
        yield client


@pytest.fixture
def room_id() -> str:
    """Sample room ID for tests."""
    return "TEST01"


@pytest.fixture
def player_data() -> dict:
    """Sample player data."""
    return {"id": "player-123", "name": "Test Player"}


@pytest.fixture
def mock_websocket() -> TestWebSocket:
    """Lightweight websocket for GameRoom unit tests."""
    return TestWebSocket()


@pytest.fixture
async def game_room(room_id: str) -> AsyncGenerator[GameRoom]:
    """Create a fresh game room for testing."""
    room = GameRoom(room_id)
    room.start_idle_check()
    yield room
    await room.stop_idle_check()


@pytest.fixture
async def room_with_players(game_room: GameRoom) -> GameRoom:
    """Game room with two players already joined."""
    ws1 = TestWebSocket()
    ws2 = TestWebSocket()

    await game_room.add_player("player-1", "Alice", as_websocket(ws1))
    await game_room.add_player("player-2", "Bob", as_websocket(ws2))

    return game_room


@pytest.fixture
def make_ws() -> Callable[..., TestWebSocket]:
    """Factory that creates lightweight websocket test doubles."""

    def _factory(*, send_error: Exception | None = None) -> TestWebSocket:
        return TestWebSocket(send_error=send_error)

    return _factory


@pytest.fixture
def room_manager() -> RoomManager:
    """Fresh room manager instance."""
    return RoomManager()


@pytest.fixture
async def managed_room_manager() -> AsyncGenerator[RoomManager]:
    """RoomManager with lifecycle management."""
    manager = RoomManager()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def test_db(
    request: pytest.FixtureRequest,
    fake_db_store: _FakeDatabaseStore,
) -> AsyncGenerator[FakeAsyncSession | AsyncSession]:
    """Provide either a fake or real session for direct test setup/assertions."""
    if _is_integration_test(request):
        async with database.get_session_maker()() as session:
            yield session
            await session.rollback()
        return

    session = FakeAsyncSession(fake_db_store)
    yield session
    await session.rollback()


@pytest.fixture
def sample_messages() -> dict:
    """Collection of sample game messages."""
    return {
        "join": {"type": "join", "playerId": "player-123", "name": "Test Player"},
        "start_game": {"type": "start_game", "difficulty": "medium", "rounds": 5, "drawingTimeLimit": 60},
        "start_round": {
            "type": "start_round",
            "round": 1,
            "Prompts": {"player-1": {"category": "Animals", "items": ["cat", "dog", "bird"]}},
        },
        "draw_stroke": {
            "type": "draw_stroke",
            "playerId": "player-1",
            "stroke": {"color": "#000000", "width": 2, "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}]},
        },
        "heartbeat": {"type": "heartbeat", "playerId": "player-1"},
        "settings_update": {"type": "settings_update", "difficulty": "hard", "rounds": 7, "drawingTimeLimit": 45},
        "player_ready": {"type": "player_ready", "playerId": "player-1"},
        "restart_game": {"type": "restart_game"},
    }
