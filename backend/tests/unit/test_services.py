"""Focused tests for service-layer helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock

from app.categories import service as category_service
from app.core.config import settings
from app.core.types import GamePhase
from app.rooms import actions as websocket_action_service
from app.rooms import kick_vote as kick_vote_service
from app.rooms import lifecycle as room_lifecycle_service
from app.rooms import player_lifecycle as player_lifecycle_service
from app.rooms import rounds as round_service
from app.rooms import router as room_service
from app.rooms import ws_router as websocket_service
from app.rooms.manager import GameRoom, RoomManager, room_manager
from app.rooms.protocol import HeartbeatEvent, RequestGameStateEvent, RoomStateEvent
from app.rooms.session import RoomWebSocketSession
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.constants import ROOM_42, ROOM_HIBERNATE, ROOM_STATE, ROUND_COMPLETE

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest
    from fastapi import WebSocket
    from pytest_mock import MockerFixture

    from tests.support import TestWebSocket


class TestRoomService:
    """Focused tests for RoomService methods that don't require WebSocket context."""

    async def test_get_random_joinable_room_returns_counts(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that get_random_joinable_room returns the correct player count for a room with players."""
        room = room_manager.get_or_create_room(ROOM_42)
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))

        response = await room_service.get_random_joinable_room()

        assert response.room_code == ROOM_42
        assert response.player_count == 1


class TestKickVoteService:
    """Focused tests for KickVoteService methods."""

    async def test_cleanup_expired_votes_removes_only_elapsed_votes(self) -> None:
        """Test that cleanup_expired_votes removes only the votes that have expired and leaves active votes intact."""
        room = GameRoom("ROOM-KICK")
        room.active_kick_votes = {
            "expired-player": kick_vote_service.KickVote(
                target_player_id="expired-player",
                target_player_name="Expired",
                initiated_by="host-1",
                expires_at=time.time() - 1,
            ),
            "active-player": kick_vote_service.KickVote(
                target_player_id="active-player",
                target_player_name="Active",
                initiated_by="host-1",
                expires_at=time.time() + 30,
            ),
        }

        removed = kick_vote_service.cleanup_expired_votes(room)

        assert removed == 1
        assert list(room.active_kick_votes) == ["active-player"]


class TestRoomLifecycleService:
    """Focused tests for RoomLifecycleService methods that don't require WebSocket context."""

    async def test_run_cleanup_hibernates_empty_room_after_threshold(
        self, make_ws: Callable[..., TestWebSocket]
    ) -> None:
        """Hibernate a room once it stays empty long enough."""
        manager = RoomManager()
        room = manager.get_or_create_room(ROOM_HIBERNATE)
        await room.add_player("player-1", "Player 1", cast("WebSocket", make_ws()))
        await room.remove_player("player-1")
        room.emptied_at = time.time() - (settings.room_hibernation_delay_seconds + 5)

        hibernated_count, removed_count = await room_lifecycle_service.run_cleanup(manager)

        assert hibernated_count == 1
        assert removed_count == 0
        assert room.is_hibernated


class TestRoundService:
    """Focused tests for RoundService methods."""

    async def test_score_round_updates_scores_and_returns_broadcast_event(
        self,
        make_ws: Callable[..., TestWebSocket],
        mocker: MockerFixture,
    ) -> None:
        """Score a round and return the broadcast event."""
        room = GameRoom("ROOM-SCORE")
        await room.add_player("player-1", "Alice", cast("WebSocket", make_ws()))
        await room.add_player("player-2", "Bob", cast("WebSocket", make_ws()))
        room.metadata.current_round = 1
        room.metadata.max_rounds = 3
        room.metadata.player_assignments = {
            "player-2": PlayerPromptAssignmentState(
                category_id=1,
                category="Animals",
                item_ids=[11, 12],
                items=["cat", "dog"],
                alternatives={},
            ),
        }
        room.metadata.guess_submissions = [
            GuessSubmissionState(player_id="player-1", target_player_id="player-2", guesses=["cat", "dog"]),
        ]

        mocker.patch.object(
            category_service,
            "get_localized_scoring_targets",
            new=AsyncMock(
                return_value=category_service.LocalizedScoringTargets(
                    category_id=1,
                    category_name="Animals",
                    targets=[
                        category_service.GuessTarget(item_id=11, label="cat", aliases=[]),
                        category_service.GuessTarget(item_id=12, label="dog", aliases=[]),
                    ],
                )
            ),
        )

        event = await round_service.score_round(room, AsyncMock())

        assert event.type == ROUND_COMPLETE
        assert event.scores == {"player-1": 20, "player-2": 20}
        assert event.results[0].correct_guesses == 2
        assert room.metadata.game_phase == GamePhase.ROUND_RESULTS
        assert room.metadata.player_scores == {"player-1": 20, "player-2": 20}


class TestPlayerLifecycleService:
    """Focused tests for PlayerLifecycleService methods that don't require WebSocket context."""

    async def test_is_host_reflects_current_host_assignment(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that is_host correctly identifies the host player based on the current room state."""
        room = GameRoom("ROOM-HOST")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))

        assert player_lifecycle_service.is_host(room, "host-1")
        assert not player_lifecycle_service.is_host(room, "other-player")


class TestWebSocketService:
    """Focused tests for WebSocketService methods."""

    async def test_handle_room_websocket_connection_runs_and_disconnects(self, mocker: MockerFixture) -> None:
        """Initialize a websocket session, run it, and handle disconnects."""
        websocket = AsyncMock()
        websocket.cookies = {}
        room = GameRoom("ROOM_WS")

        mock_session_cls = mocker.patch.object(websocket_service, "RoomWebSocketSession")
        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session

        mock_manager = mocker.MagicMock()
        mock_manager.get_or_create_room.return_value = room
        mocker.patch.object(websocket_service, "room_manager", mock_manager)

        fake_db = AsyncMock()
        fake_db.__aenter__.return_value = fake_db
        mocker.patch.object(websocket_service, "get_session_maker", return_value=lambda: fake_db)
        mocker.patch.object(websocket_service, "get_user_by_session", new=AsyncMock(return_value=None))

        await websocket_service.websocket_endpoint(websocket, room_id="ROOM_WS")

        websocket.accept.assert_awaited_once()
        mock_session_cls.assert_called_once_with(room, websocket, current_user=None)
        mock_session.run.assert_awaited_once()
        mock_session.on_disconnect.assert_awaited_once()


@dataclass
class _FakeSession:
    room: GameRoom
    websocket: object
    player_id: str | None = None
    error_calls: list[tuple[str, str, str]] = field(default_factory=list)

    def is_host(self) -> bool:
        return self.room.is_host(self.player_id)

    async def send_error(self, event_type: str, error: str, message: str) -> None:
        self.error_calls.append((event_type, error, message))


class TestWebSocketActionService:
    """Focused tests for WebSocket action handlers that use the protocol context."""

    async def test_require_host_uses_protocol_context(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that require_host correctly checks the session's host status and sends an error if not the host."""
        room = GameRoom("ROOM-ACT")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))
        session = _FakeSession(room=room, websocket=AsyncMock(), player_id="not-host")

        allowed = await websocket_action_service.require_host(cast("RoomWebSocketSession", session), "start the game")

        assert not allowed
        assert session.error_calls == [("permission_error", "host_only", "Only the host can start the game.")]

    async def test_handle_request_game_state_uses_protocol_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that handle_request_game_state sends the current room state to the requesting session's websocket."""
        room = GameRoom("ROOM-STATE")
        websocket = AsyncMock()
        session = _FakeSession(room=room, websocket=websocket)
        sent_messages: list[RoomStateEvent] = []

        async def fake_send_ws_message(websocket_arg: object, message: RoomStateEvent) -> None:
            assert websocket_arg is websocket
            sent_messages.append(message)

        monkeypatch.setattr(websocket_action_service, "send_ws_message", fake_send_ws_message)

        await websocket_action_service.handle_request_game_state(
            cast("RoomWebSocketSession", session), RequestGameStateEvent(type="request_game_state")
        )

        assert len(sent_messages) == 1
        assert sent_messages[0].type == ROOM_STATE

    async def test_dispatch_event_ignores_heartbeat(self) -> None:
        """Test that dispatch_event ignores HeartbeatEvent without error."""
        room = GameRoom("ROOM-HEARTBEAT")
        session = _FakeSession(room=room, websocket=AsyncMock())

        await websocket_action_service.dispatch_event(
            cast("RoomWebSocketSession", session), HeartbeatEvent(type="heartbeat")
        )

        assert session.error_calls == []
