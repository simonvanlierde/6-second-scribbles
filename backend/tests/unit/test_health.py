"""The health endpoint's status code tracks its dependencies."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from app.system import router as system_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    import pytest
    from fakeredis import FakeRedis
    from fastapi.testclient import TestClient

HEALTH_PATH = "/api/health"
OK = "ok"
ERROR = "error"
DEGRADED = "degraded"


def _session_maker(*, fails: bool) -> Callable[[], Callable[[], object]]:
    """Stand in for get_session_maker: a session whose SELECT 1 works or raises."""

    @asynccontextmanager
    async def session() -> AsyncGenerator[AsyncMock]:
        db = AsyncMock()
        if fails:
            db.execute.side_effect = ConnectionRefusedError("database down")
        yield db

    return lambda: session


def test_health_ok_returns_200(monkeypatch: pytest.MonkeyPatch, test_client: TestClient) -> None:
    """Both dependencies up: 200 and status ok."""
    monkeypatch.setattr(system_router, "get_session_maker", _session_maker(fails=False))

    response = test_client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json()["status"] == OK


def test_health_database_down_returns_503(monkeypatch: pytest.MonkeyPatch, test_client: TestClient) -> None:
    """A failing database makes the check fail, so Compose marks the backend unhealthy."""
    monkeypatch.setattr(system_router, "get_session_maker", _session_maker(fails=True))

    response = test_client.get(HEALTH_PATH)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == DEGRADED
    assert payload["database"] == ERROR
    assert payload["cache"] == OK


def test_health_cache_down_returns_503(
    monkeypatch: pytest.MonkeyPatch, test_client: TestClient, fake_redis: FakeRedis
) -> None:
    """A failing Redis ping also answers 503."""
    monkeypatch.setattr(system_router, "get_session_maker", _session_maker(fails=False))
    monkeypatch.setattr(fake_redis, "ping", AsyncMock(side_effect=ConnectionError("cache down")))

    response = test_client.get(HEALTH_PATH)

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == DEGRADED
    assert payload["database"] == OK
    assert payload["cache"] == ERROR
