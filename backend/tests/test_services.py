"""Focused tests for service-layer helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.types import GamePhase
from app.categories import service as category_service
from app.categories.models import Card, Category
from app.categories.schemas import GuessRequest
from app.rooms import (
    actions as websocket_action_service,
)
from app.rooms import (
    kick_vote as kick_vote_service,
)
from app.rooms import (
    lifecycle as room_lifecycle_service,
)
from app.rooms import (
    mutations as room_mutation_service,
)
from app.rooms import (
    player_lifecycle as player_lifecycle_service,
)
from app.rooms import (
    rounds as round_service,
)
from app.rooms import (
    router as room_service,
)
from app.rooms import (
    ws_router as websocket_service,
)
from app.rooms.manager import GameRoom, PlayerInfo, RoomManager, room_manager
from app.rooms.protocol import HeartbeatEvent, RequestGameStateEvent
from app.rooms.schemas import CustomCategoryCreate
from app.rooms.state import GuessSubmissionState, PlayerCardState

if TYPE_CHECKING:
    from fastapi import WebSocket


class TestCategoryService:
    async def test_list_categories_filters_by_difficulty_and_language(self, test_db) -> None:
        test_db.add(Category(name="Easy EN", difficulty="easy", language="en"))
        test_db.add(Category(name="Easy FR", difficulty="easy", language="fr"))
        test_db.add(Category(name="Hard EN", difficulty="hard", language="en"))
        await test_db.commit()

        response = await category_service.list_categories(test_db, difficulty="easy", language="en")

        assert response.count == 1
        assert [category.name for category in response.categories] == ["Easy EN"]

    async def test_get_category_detail_returns_cards(self, test_db) -> None:
        category = Category(name="Animals", difficulty="medium", language="en")
        test_db.add(category)
        await test_db.flush()
        test_db.add(Card(category_id=category.id, item="cat", alternatives=["kitty"]))
        test_db.add(Card(category_id=category.id, item="dog", alternatives=[]))
        await test_db.commit()

        response = await category_service.get_category_detail(test_db, category_id=category.id)

        assert response.category.name == "Animals"
        assert response.items == ["cat", "dog"]
        assert response.cards[0].alternatives == ["kitty"]

    async def test_get_random_category_cards_includes_room_categories(self, test_db, monkeypatch) -> None:
        global_category = Category(name="Global", difficulty="medium", language="en")
        room_category = Category(name="Room", difficulty="medium", language="en", room_id="ROOM1", created_by="host")
        test_db.add(global_category)
        test_db.add(room_category)
        await test_db.flush()
        test_db.add(Card(category_id=global_category.id, item="apple", alternatives=[]))
        test_db.add(Card(category_id=room_category.id, item="pear", alternatives=["pome"]))
        await test_db.commit()

        monkeypatch.setattr(
            category_service.random,
            "sample",
            lambda categories, total_needed: list(categories)[:total_needed],
        )

        response = await category_service.get_random_category_cards(
            test_db,
            difficulty="medium",
            count=1,
            player_count=2,
            room_id="ROOM1",
            language="en",
        )

        assert response.includes_custom is True
        assert {card_set.category for card_set in response.categories.values()} == {"Global", "Room"}

    def test_score_guess_request_maps_match_details(self) -> None:
        response = category_service.score_guess_request(
            GuessRequest(
                guesses=["colour"],
                correct_answers=["color"],
                alternatives={"color": ["colour"]},
            )
        )

        assert response.score == 1
        assert response.matches[0].method == "alternative"


class TestRoomService:
    async def test_get_random_joinable_room_returns_counts(self, make_ws) -> None:
        room = room_manager.get_or_create_room("ROOM42")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))

        response = await room_service.get_random_joinable_room()

        assert response.room_code == "ROOM42"
        assert response.player_count == 1

    async def test_create_room_custom_category_broadcasts_summary(self, test_db, make_ws) -> None:
        room = room_manager.get_or_create_room("ROOM99")
        ws = make_ws()
        room.players["host-1"] = PlayerInfo(id="host-1", name="Host", websocket=cast("WebSocket", ws))
        room.host_id = "host-1"

        response = await room_service.create_room_custom_category(
            test_db,
            room_id="ROOM99",
            category_data=CustomCategoryCreate(
                name="Creatures",
                items=["otter", "stoat", "lynx", "ibis", "tapir"],
                difficulty="medium",
                created_by="host-1",
            ),
        )

        assert response.success is True
        assert response.category.name == "Creatures"
        assert ws.sent_texts

    async def test_delete_room_custom_category_requires_player_id(self, test_db) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await room_service.delete_room_custom_category(test_db, room_id="ROOM1", category_id=1, player_id=None)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "Player ID is required"


class TestKickVoteService:
    async def test_cleanup_expired_votes_removes_only_elapsed_votes(self) -> None:
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
    async def test_run_cleanup_hibernates_empty_room_after_threshold(self, make_ws) -> None:
        manager = RoomManager()
        room = manager.get_or_create_room("ROOM-HIBERNATE")
        await room.add_player("player-1", "Player 1", cast("WebSocket", make_ws()))
        await room.remove_player("player-1")
        room._emptied_at = time.time() - 65

        hibernated_count, removed_count = await room_lifecycle_service.run_cleanup(manager)

        assert hibernated_count == 1
        assert removed_count == 0
        assert room.is_hibernated is True


class TestRoundService:
    async def test_score_round_updates_scores_and_returns_broadcast_event(self, make_ws) -> None:
        room = GameRoom("ROOM-SCORE")
        await room.add_player("player-1", "Alice", cast("WebSocket", make_ws()))
        await room.add_player("player-2", "Bob", cast("WebSocket", make_ws()))
        room.metadata.current_round = 1
        room.metadata.max_rounds = 3
        room.metadata.player_cards = {
            "player-2": PlayerCardState(category="Animals", items=["cat", "dog"], alternatives={}, is_custom=False),
        }
        room.metadata.guess_submissions = [
            GuessSubmissionState(player_id="player-1", target_player_id="player-2", guesses=["cat", "dog"]),
        ]

        event = round_service.score_round(room)

        assert event.type == "round_complete"
        assert event.scores == {"player-1": 20, "player-2": 20}
        assert event.results[0].correct_guesses == 2
        assert room.metadata.game_phase == GamePhase.SCORING
        assert room.metadata.player_scores == {"player-1": 20, "player-2": 20}


class TestPlayerLifecycleService:
    async def test_is_host_reflects_current_host_assignment(self, make_ws) -> None:
        room = GameRoom("ROOM-HOST")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))

        assert player_lifecycle_service.is_host(room, "host-1") is True
        assert player_lifecycle_service.is_host(room, "other-player") is False


class TestRoomMutationService:
    def test_apply_settings_update_updates_only_provided_fields(self) -> None:
        room = GameRoom("ROOM-MUTATE")
        room.metadata.difficulty = "medium"
        room.metadata.max_rounds = 5
        room.metadata.drawing_time_limit = 30

        room_mutation_service.apply_settings_update(
            room,
            difficulty="hard",
            rounds=None,
            drawing_time_limit=45,
        )

        assert room.metadata.difficulty == "hard"
        assert room.metadata.max_rounds == 5
        assert room.metadata.drawing_time_limit == 45


class TestWebSocketService:
    async def test_handle_room_websocket_connection_runs_and_disconnects(self, monkeypatch) -> None:
        websocket = AsyncMock()
        room = GameRoom("ROOM_WS")
        fake_manager = SimpleNamespace(get_or_create_room=lambda _room_id: room)
        events: list[str] = []

        class FakeSession:
            def __init__(self, room_arg, websocket_arg) -> None:
                assert room_arg is room
                assert websocket_arg is websocket

            async def run(self) -> None:
                events.append("run")

            async def on_disconnect(self) -> None:
                events.append("disconnect")

        monkeypatch.setattr(websocket_service, "room_manager", fake_manager)
        monkeypatch.setattr(websocket_service, "RoomWebSocketSession", FakeSession)

        await websocket_service.websocket_endpoint(websocket, room_id="ROOM_WS")

        websocket.accept.assert_awaited_once()
        assert events == ["run", "disconnect"]


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
    async def test_require_host_uses_protocol_context(self, make_ws) -> None:
        room = GameRoom("ROOM-ACT")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))
        session = _FakeSession(room=room, websocket=AsyncMock(), player_id="not-host")

        allowed = await websocket_action_service.require_host(session, "start the game")  # ty: ignore[invalid-argument-type]

        assert allowed is False
        assert session.error_calls == [("permission_error", "host_only", "Only the host can start the game.")]

    async def test_handle_request_game_state_uses_protocol_context(self, monkeypatch) -> None:
        room = GameRoom("ROOM-STATE")
        websocket = AsyncMock()
        session = _FakeSession(room=room, websocket=websocket)
        sent_messages: list[Any] = []

        async def fake_send_ws_message(websocket_arg, message) -> None:
            assert websocket_arg is websocket
            sent_messages.append(message)

        monkeypatch.setattr(websocket_action_service, "send_ws_message", fake_send_ws_message)

        await websocket_action_service.handle_request_game_state(
            session,  # ty: ignore[invalid-argument-type]
            RequestGameStateEvent(type="request_game_state"),
        )

        assert len(sent_messages) == 1
        assert sent_messages[0].type == "room_state"

    async def test_dispatch_event_ignores_heartbeat(self) -> None:
        room = GameRoom("ROOM-HEARTBEAT")
        session = _FakeSession(room=room, websocket=AsyncMock())

        await websocket_action_service.dispatch_event(
            session,  # ty: ignore[invalid-argument-type]
            HeartbeatEvent(type="heartbeat"),
        )

        assert session.error_calls == []
