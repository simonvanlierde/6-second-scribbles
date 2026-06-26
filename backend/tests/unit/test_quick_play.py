"""Tests for the POST /rooms/quick-play endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.config import settings
from app.rooms import router as room_router
from tests.helpers import JoinedPlayer, joined_players

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def patch_router_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Patch the router's local ``get_redis`` binding with a fresh FakeRedis.

    The conftest autouse fixture patches ``app.core.redis.get_redis`` but the
    router imports the symbol directly, so its local binding needs its own
    patch for POST endpoints that hit Redis.
    """
    fake = FakeRedis()
    monkeypatch.setattr(room_router, "get_redis", AsyncMock(return_value=fake))
    return fake


OK = 200
TOO_MANY_REQUESTS = 429
SERVICE_UNAVAILABLE = 503
ROOM_CODE_LEN = 6
KIND_CREATED = "created"
KIND_EXISTING = "existing"


class TestQuickPlay:
    """Quick-play returns an existing joinable public room or creates a fresh one."""

    def test_creates_room_when_none_available(self, test_client: TestClient) -> None:
        """With no existing rooms, quick-play creates a fresh public room."""
        response = test_client.post("/api/rooms/quick-play")
        assert response.status_code == OK
        body = response.json()
        assert body["kind"] == KIND_CREATED
        assert body["room_code"]
        assert len(body["room_code"]) == ROOM_CODE_LEN

    def test_returns_existing_room_when_one_has_space(self, test_client: TestClient) -> None:
        """A public room in lobby with space is reused rather than creating a new one."""
        room_id = "QUICK_01"
        with joined_players(test_client, room_id, [JoinedPlayer("player1", "Test Player")]):
            response = test_client.post("/api/rooms/quick-play")
            assert response.status_code == OK
            body = response.json()
            assert body["kind"] == KIND_EXISTING
            assert body["room_code"] == room_id


class TestRoomCreationAtCapacity:
    """Room-creating endpoints return 503 when the global room cap is reached."""

    def test_quick_play_returns_503_at_capacity(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Quick-play surfaces a 503 when no new room can be created."""
        monkeypatch.setattr(settings, "max_total_rooms", 0)
        response = test_client.post("/api/rooms/quick-play")
        assert response.status_code == SERVICE_UNAVAILABLE

    def test_create_room_returns_503_at_capacity(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Create-room surfaces a 503 when no new room can be created."""
        monkeypatch.setattr(settings, "max_total_rooms", 0)
        response = test_client.post("/api/rooms/")
        assert response.status_code == SERVICE_UNAVAILABLE


class TestRoomCreationRateLimit:
    """Room-creating endpoints enforce a per-IP rate limit."""

    def test_quick_play_is_rate_limited(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Quick-play returns 429 once the per-IP limit is exceeded."""
        monkeypatch.setattr(settings, "room_creation_rate_limit", 1)
        monkeypatch.setattr(settings, "room_creation_rate_window_seconds", 60)

        first = test_client.post("/api/rooms/quick-play")
        second = test_client.post("/api/rooms/quick-play")

        assert first.status_code == OK
        assert second.status_code == TOO_MANY_REQUESTS

    def test_create_room_is_rate_limited(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Create-room returns 429 once the per-IP limit is exceeded."""
        monkeypatch.setattr(settings, "room_creation_rate_limit", 1)
        monkeypatch.setattr(settings, "room_creation_rate_window_seconds", 60)

        first = test_client.post("/api/rooms/")
        second = test_client.post("/api/rooms/")

        assert first.status_code == OK
        assert second.status_code == TOO_MANY_REQUESTS
