"""Focused tests for service-layer helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api_schemas import CustomCategoryCreate, GuessRequest
from app.db_models import Card, Category
from app.game_room import GameRoom, PlayerInfo, room_manager
from app.services import category_service, room_service, websocket_action_service, websocket_service
from app.ws_protocol import RequestGameStateEvent

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


class TestWebSocketService:
    async def test_handle_room_websocket_connection_runs_and_disconnects(self, monkeypatch) -> None:
        websocket = AsyncMock()
        room = GameRoom("ROOMWS")
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

        await websocket_service.handle_room_websocket_connection(websocket, room_id="ROOMWS")

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
    async def test_reject_if_not_host_uses_protocol_context(self, make_ws) -> None:
        room = GameRoom("ROOM-ACT")
        await room.add_player("host-1", "Host", cast("WebSocket", make_ws()))
        session = _FakeSession(room=room, websocket=AsyncMock(), player_id="not-host")

        rejected = await websocket_action_service.reject_if_not_host(session, "start the game")

        assert rejected is True
        assert session.error_calls == [("permission_error", "host_only", "Only the host can start the game.")]

    async def test_handle_request_game_state_uses_protocol_context(self, monkeypatch) -> None:
        room = GameRoom("ROOM-STATE")
        websocket = AsyncMock()
        session = _FakeSession(room=room, websocket=websocket)
        sent_messages: list[object] = []

        async def fake_send_ws_message(websocket_arg, message) -> None:
            assert websocket_arg is websocket
            sent_messages.append(message)

        monkeypatch.setattr(websocket_action_service, "send_ws_message", fake_send_ws_message)

        await websocket_action_service.handle_request_game_state(
            session,
            RequestGameStateEvent(type="request_game_state", playerId=None),
        )

        assert len(sent_messages) == 1
        assert sent_messages[0].type == "room_state"
