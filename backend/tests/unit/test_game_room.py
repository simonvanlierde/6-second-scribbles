"""Tests for game room management functionality."""
# cspell: ignore rejoiner

import json
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.categories import service as category_service
from app.categories.schemas import CategorySelectionResponse, SelectedCategorySet
from app.core.config import settings
from app.core.types import GamePhase
from app.rooms import manager as manager_module
from app.rooms import rounds
from app.rooms.kick_vote import HOST_CANNOT_BE_VOTE_KICKED_ERROR, VOTE_KICK_PUBLIC_ONLY_ERROR, get_required_votes
from app.rooms.manager import GameRoom, PlayerInfo, RoomManager
from app.rooms.protocol import WebSocketMessage
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.constants import (
    HOST_ONE,
    KICK_VOTE_STARTED,
    MEDIUM,
    PLAYER_FOUR_ID,
    PLAYER_FOUR_NAME,
    PLAYER_ONE_ID,
    PLAYER_ONE_NAME,
    PLAYER_THREE_ID,
    PLAYER_THREE_NAME,
    PLAYER_TWO_ID,
    PLAYER_TWO_NAME,
    READY_STATUS,
    ROOM_NO_CATEGORIES,
    ROOM_STATE,
    TEST_ROOM_ID,
)
from tests.support import as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support import TestWebSocket

EXPIRES_AT = "expiresAt"
HOST_CHANGED = "host_changed"


def _scheduler_tasks(scheduler: object) -> dict[str, object | None]:
    return vars(scheduler)


class TestGameRoom:
    """Test suite for GameRoom class."""

    async def test_create_room(self, room_id: str) -> None:
        """Test creating a new game room."""
        room = GameRoom(room_id)
        assert room.room_id == room_id
        assert len(room.players) == 0
        assert room.host_id is None
        assert room.metadata.game_phase == GamePhase.LOBBY

    async def test_add_first_player_becomes_host(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test that the first player to join becomes the host."""
        player_id = PLAYER_ONE_ID
        player_name = PLAYER_ONE_NAME

        await game_room.add_player(player_id, player_name, as_websocket(mock_websocket))

        assert len(game_room.players) == 1
        assert game_room.host_id == player_id
        assert game_room.players[player_id].name == player_name

    async def test_add_multiple_players(self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test adding multiple players to a room."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await game_room.add_player(PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))

        assert len(game_room.players) == 3
        assert game_room.host_id == PLAYER_ONE_ID  # First player is host

    async def test_remove_player(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test removing a player from the room."""
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert len(game_room.players) == 1

        await game_room.remove_player(PLAYER_ONE_ID)
        assert len(game_room.players) == 0

    async def test_host_transfer_on_host_leave(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that host is transferred when the host leaves."""
        ws1, ws2 = make_ws(), make_ws()
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 0)

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

        assert game_room.host_id == PLAYER_ONE_ID

        await game_room.remove_player(PLAYER_ONE_ID)
        assert game_room.pending_host_transfer is not None
        await game_room.pending_host_transfer

        assert game_room.host_id == PLAYER_TWO_ID

        # Verify the host_changed message content was broadcast to Bob
        messages = [json.loads(message) for message in ws2.sent_texts]
        host_changed = next((m for m in messages if m.get("type") == HOST_CHANGED), None)
        assert host_changed is not None
        assert host_changed["newHostId"] == PLAYER_TWO_ID

    async def test_no_host_when_room_empty(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test that host_id is None when all players leave."""
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        await game_room.remove_player(PLAYER_ONE_ID)

        assert game_room.host_id is None
        assert len(game_room.players) == 0

    async def test_player_id_cannot_be_claimed_by_another_user(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """A player_id bound to one user rejects a join from a different user."""
        ws_alice, ws_mallory = make_ws(), make_ws()
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws_alice), user_id="user-alice")

        with pytest.raises(ValueError, match="identity_conflict"):
            await game_room.add_player(PLAYER_ONE_ID, "Mallory", as_websocket(ws_mallory), user_id="user-mallory")

        # Alice keeps her seat, host role, and live socket — no takeover occurred.
        assert game_room.host_id == PLAYER_ONE_ID
        assert game_room.players[PLAYER_ONE_ID].websocket is as_websocket(ws_alice)

    async def test_same_user_can_rejoin_own_player_id(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """The legitimate owner reconnecting with the same player_id is not blocked."""
        ws1, ws2 = make_ws(), make_ws()
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1), user_id="user-alice")

        # Same user, same player_id, new socket (e.g. a page refresh): must succeed
        # and retain the host role.
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws2), user_id="user-alice")

        assert game_room.host_id == PLAYER_ONE_ID
        assert game_room.players[PLAYER_ONE_ID].websocket is as_websocket(ws2)

    async def test_different_user_cannot_seize_host_after_owner_leaves(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Reusing a departed host's freed player_id must not grant the host role."""
        ws_alice, ws_bob, ws_mallory = make_ws(), make_ws(), make_ws()
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 0)

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws_alice), user_id="user-alice")
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws_bob), user_id="user-bob")

        # Host leaves explicitly; a transfer is pending and host_id still lingers.
        await game_room.remove_player(PLAYER_ONE_ID)
        assert game_room.pending_host_transfer is not None

        # Mallory grabs the freed player_id under a different account. She joins as a
        # plain player and must not inherit the lingering host role.
        _player, is_reconnecting_host = await game_room.add_player(
            PLAYER_ONE_ID,
            "Mallory",
            as_websocket(ws_mallory),
            user_id="user-mallory",
        )
        assert is_reconnecting_host is False
        assert game_room.host_id != PLAYER_ONE_ID

        # The pending transfer promotes the genuine remaining player, not Mallory.
        await game_room.pending_host_transfer
        assert game_room.host_id == PLAYER_TWO_ID

    async def test_update_player_activity(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test updating player's last activity timestamp."""
        with patch("app.rooms.manager.time.time", side_effect=[1000.0, 1000.0, 1001.0]):
            await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
            initial_time = game_room.players[PLAYER_ONE_ID].last_activity

            game_room.update_player_activity(PLAYER_ONE_ID)
            updated_time = game_room.players[PLAYER_ONE_ID].last_activity

        assert updated_time > initial_time

    async def test_broadcast_to_all_players(self, room_with_players: GameRoom) -> None:
        """Test broadcasting a message to all players."""
        message = cast("WebSocketMessage", {"type": "test", "data": "hello"})

        await room_with_players.broadcast(message)

        for player in room_with_players.players.values():
            assert cast("TestWebSocket", player.websocket).sent_texts == [json.dumps(message)]

    async def test_broadcast_exclude_player(self, room_with_players: GameRoom) -> None:
        """Test broadcasting with exclusion."""
        message = cast("WebSocketMessage", {"type": "test", "data": "hello"})

        await room_with_players.broadcast(message, exclude=PLAYER_ONE_ID)

        player1 = room_with_players.players[PLAYER_ONE_ID]
        player2 = room_with_players.players[PLAYER_TWO_ID]

        assert cast("TestWebSocket", player1.websocket).sent_texts == []
        assert cast("TestWebSocket", player2.websocket).sent_texts == [json.dumps(message)]

    async def test_send_to_specific_player(self, room_with_players: GameRoom) -> None:
        """Test sending a message to a specific player."""
        message = cast("WebSocketMessage", {"type": "test", "data": "hello"})

        await room_with_players.send_to_player(PLAYER_ONE_ID, message)

        player1 = room_with_players.players[PLAYER_ONE_ID]
        player2 = room_with_players.players[PLAYER_TWO_ID]

        assert cast("TestWebSocket", player1.websocket).sent_texts == [json.dumps(message)]
        assert cast("TestWebSocket", player2.websocket).sent_texts == []

    async def test_get_player_list(self, room_with_players: GameRoom) -> None:
        """Test getting the list of players."""
        player_list = room_with_players.get_player_list()

        assert len(player_list) == 2
        ids_and_names = {(p.id, p.name) for p in player_list}
        assert (PLAYER_ONE_ID, PLAYER_ONE_NAME) in ids_and_names
        assert (PLAYER_TWO_ID, PLAYER_TWO_NAME) in ids_and_names
        # Each player should have been assigned a colour token.
        for p in player_list:
            assert p.color is not None
            assert p.color.startswith("var(--avatar-")

    async def test_is_empty(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test checking if room is empty."""
        assert game_room.is_empty()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert not game_room.is_empty()

        await game_room.remove_player(PLAYER_ONE_ID)
        assert game_room.is_empty()

    async def test_metadata_initialization(self, game_room: GameRoom) -> None:
        """Test that room metadata is properly initialized."""
        assert game_room.metadata.game_phase == GamePhase.LOBBY
        assert game_room.metadata.difficulty == MEDIUM
        assert game_room.metadata.max_rounds == 5
        assert game_room.metadata.pad_visibility
        assert len(game_room.metadata.ready_players) == 0

    async def test_ready_players_tracking(self, room_with_players: GameRoom) -> None:
        """Test tracking ready players."""
        assert len(room_with_players.metadata.ready_players) == 0

        room_with_players.metadata.ready_players.add(PLAYER_ONE_ID)
        assert len(room_with_players.metadata.ready_players) == 1

        room_with_players.metadata.ready_players.add(PLAYER_TWO_ID)
        assert len(room_with_players.metadata.ready_players) == 2

    async def test_mark_player_ready_returns_ready_status_payload(self, room_with_players: GameRoom) -> None:
        """Test ready-state payload serialization uses websocket aliases."""
        payload = room_with_players.mark_player_ready("player-1")

        assert payload.model_dump(by_alias=True, exclude_none=True) == {
            "type": READY_STATUS,
            "readyCount": 1,
            "totalPlayers": 2,
        }

    async def test_start_guessing_resets_ready_players_and_sets_timestamp(self, room_with_players: GameRoom) -> None:
        """Guessing starts with a fresh ready state and an explicit phase start time."""
        room_with_players.metadata.ready_players.update({"player-1", "player-2"})

        timeout_seconds = room_with_players.start_guessing()

        assert timeout_seconds == 60
        assert room_with_players.metadata.game_phase == GamePhase.GUESSING
        assert room_with_players.metadata.ready_players == set()
        assert room_with_players.metadata.guessing_start_time is not None

    async def test_broadcast_handles_disconnected_player(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test that broadcast handles disconnected players gracefully."""
        ws1 = make_ws()
        ws2 = make_ws(send_error=Exception("Connection closed"))

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

        message = cast("WebSocketMessage", {"type": "test"})
        await game_room.broadcast(message)

        # A failed send marks the player disconnected (kept as a reconnecting
        # presence) rather than removing them; the receive loop will finalize it.
        assert PLAYER_TWO_ID in game_room.players
        assert game_room.players[PLAYER_TWO_ID].connected is False
        assert PLAYER_ONE_ID in game_room.players

    async def test_room_marked_empty_after_all_disconnect(
        self,
        game_room: GameRoom,
        mock_websocket: TestWebSocket,
    ) -> None:
        """Test that room is marked as empty after all players disconnect.

        Note: rooms are not immediately removed — the periodic cleanup loop
        handles hibernation (1 min) and removal (5 min).
        """
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert not game_room.is_empty()

        await game_room.remove_player(PLAYER_ONE_ID)

        assert game_room.is_empty()
        assert game_room.emptied_at is not None

    async def test_start_round_with_server_cards_recovers_when_categories_missing(
        self,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the round task does not crash when no matching categories exist."""
        room = GameRoom(ROOM_NO_CATEGORIES)
        room.players[PLAYER_ONE_ID] = PlayerInfo(
            id=PLAYER_ONE_ID,
            name=PLAYER_ONE_NAME,
            websocket=as_websocket(make_ws()),
        )
        room.players[PLAYER_TWO_ID] = PlayerInfo(
            id=PLAYER_TWO_ID,
            name=PLAYER_TWO_NAME,
            websocket=as_websocket(make_ws()),
        )
        broadcast_mock = AsyncMock()
        persist_mock = AsyncMock()
        monkeypatch.setattr(room, "broadcast", broadcast_mock)
        monkeypatch.setattr(room, "persist", persist_mock)

        monkeypatch.setattr(
            category_service,
            "select_category_sets",
            AsyncMock(side_effect=HTTPException(status_code=404, detail="No categories found for difficulty: medium")),
        )

        await room.start_round_with_server_cards()

        assert room.metadata.game_phase == GamePhase.LOBBY
        broadcast_mock.assert_awaited_once()
        broadcast_call = broadcast_mock.await_args
        assert broadcast_call is not None
        assert broadcast_call.args[0].type == ROOM_STATE
        persist_mock.assert_awaited_once()

    async def test_start_round_reuses_categories_when_fewer_than_players(
        self,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rounds must start even when fewer categories are available than players."""
        room = GameRoom(ROOM_NO_CATEGORIES)
        for player_id, player_name in (
            (PLAYER_ONE_ID, PLAYER_ONE_NAME),
            (PLAYER_TWO_ID, PLAYER_TWO_NAME),
            (PLAYER_THREE_ID, PLAYER_THREE_NAME),
        ):
            room.players[player_id] = PlayerInfo(
                id=player_id,
                name=player_name,
                websocket=as_websocket(make_ws()),
            )
        monkeypatch.setattr(room, "broadcast", AsyncMock())
        monkeypatch.setattr(room, "persist", AsyncMock())

        class _FakeSession:
            async def __aenter__(self) -> object:
                return object()

            async def __aexit__(self, *args: object) -> None:
                return None

        monkeypatch.setattr(manager_module, "get_session_maker", lambda: _FakeSession)

        # Only two categories available for three players.
        selections = [
            SelectedCategorySet(
                category_id=cid,
                category_name=name,
                item_ids=[cid],
                items=[name],
                alternatives={name: []},
            )
            for cid, name in ((143, "Sports Equipment"), (144, "Weather Phenomena"))
        ]
        monkeypatch.setattr(
            category_service,
            "select_category_sets",
            AsyncMock(return_value=CategorySelectionResponse(difficulty=MEDIUM, selections=selections)),
        )
        monkeypatch.setattr(
            category_service,
            "get_localized_category_set",
            AsyncMock(
                side_effect=lambda _db, *, category_id, **_kwargs: next(
                    s for s in selections if s.category_id == category_id
                )
            ),
        )

        await room.start_round_with_server_cards()

        assert room.metadata.game_phase == GamePhase.DRAWING
        assert set(room.metadata.player_assignments.keys()) == {PLAYER_ONE_ID, PLAYER_TWO_ID, PLAYER_THREE_ID}

    async def test_initiate_kick_vote_broadcasts_modeled_payload(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test kick vote start broadcast preserves the expected protocol shape."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await game_room.add_player(PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))

        result = await game_room.initiate_kick_vote(PLAYER_TWO_ID, PLAYER_THREE_ID)

        assert result.success
        assert result.vote_id == PLAYER_THREE_ID
        messages = [json.loads(message) for message in ws1.sent_texts]
        assert messages[-1]["type"] == KICK_VOTE_STARTED
        assert messages[-1]["targetPlayerId"] == PLAYER_THREE_ID
        assert messages[-1]["targetPlayerName"] == PLAYER_THREE_NAME
        assert messages[-1]["initiatorId"] == PLAYER_TWO_ID
        assert messages[-1]["currentVotes"] == 1
        assert messages[-1]["requiredVotes"] == 2
        assert EXPIRES_AT in messages[-1]

    async def test_cast_kick_vote_returns_typed_progress_result(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test kick-vote progress returns a typed result object."""
        ws1, ws2, ws3, ws4 = make_ws(), make_ws(), make_ws(), make_ws()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await game_room.add_player(PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))
        await game_room.add_player(PLAYER_FOUR_ID, PLAYER_FOUR_NAME, as_websocket(ws4))

        start_result = await game_room.initiate_kick_vote(PLAYER_TWO_ID, PLAYER_FOUR_ID)
        assert start_result.success

        vote_result = await game_room.cast_kick_vote(PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert vote_result.success
        assert not vote_result.vote_passed
        assert vote_result.current_votes == 2
        assert vote_result.required_votes == 3

    async def test_players_cannot_vote_kick_the_host(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Non-host players must leave rather than vote-kicking the host."""
        ws1, ws2 = make_ws(), make_ws()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

        result = await game_room.initiate_kick_vote(PLAYER_TWO_ID, PLAYER_ONE_ID)

        assert not result.success
        assert result.error == HOST_CANNOT_BE_VOTE_KICKED_ERROR

    async def test_players_cannot_vote_kick_in_private_rooms(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Vote-kick stays reserved for public stranger rooms."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await game_room.add_player(PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))
        game_room.metadata.is_private = True

        result = await game_room.initiate_kick_vote(PLAYER_TWO_ID, PLAYER_THREE_ID)

        assert not result.success
        assert result.error == VOTE_KICK_PUBLIC_ONLY_ERROR

    async def test_room_state_round_trips_through_persistence_model(self, game_room: GameRoom) -> None:
        """Test persisted room state preserves structured metadata."""
        game_room.host_id = HOST_ONE
        game_room.last_host_id = HOST_ONE
        game_room.metadata.game_phase = GamePhase.DRAWING
        game_room.metadata.current_round = 2
        game_room.metadata.ready_players.add(HOST_ONE)
        game_room.metadata.submitted_players.add(PLAYER_TWO_ID)
        game_room.metadata.player_assignments = {
            PLAYER_ONE_ID: PlayerPromptAssignmentState(
                category_id=1,
                category="Animals",
                item_ids=[11, 12],
                items=["cat", "dog"],
                alternatives={"cat": ["kitty"]},
            ),
        }
        game_room.metadata.guess_submissions = [
            GuessSubmissionState(player_id=PLAYER_TWO_ID, target_player_id=PLAYER_ONE_ID, guesses=["cat"]),
        ]

        restored_room = GameRoom.from_state(game_room.to_state())

        assert restored_room.host_id == HOST_ONE
        assert restored_room.metadata.game_phase == GamePhase.DRAWING
        assert restored_room.metadata.current_round == 2
        assert restored_room.metadata.ready_players == {HOST_ONE}
        assert restored_room.metadata.submitted_players == {PLAYER_TWO_ID}
        assert restored_room.metadata.player_assignments[PLAYER_ONE_ID].alternatives == {"cat": ["kitty"]}
        assert restored_room.metadata.guess_submissions[0].player_id == PLAYER_TWO_ID
        assert restored_room.metadata.guess_submissions[0].guesses == ["cat"]


class TestRoomManager:
    """Test suite for RoomManager class."""

    def test_create_room_manager(self, room_manager: RoomManager) -> None:
        """Test creating a room manager."""
        assert len(room_manager.rooms) == 0

    async def test_get_or_create_room(self, room_manager: RoomManager) -> None:
        """Test getting or creating a room."""
        room_id = TEST_ROOM_ID

        # First call should create a new room
        room1 = room_manager.get_or_create_room(room_id)
        assert room1.room_id == room_id
        assert len(room_manager.rooms) == 1

        # Second call should return the same room
        room2 = room_manager.get_or_create_room(room_id)
        assert room1 is room2
        assert len(room_manager.rooms) == 1

    async def test_get_room(self, room_manager: RoomManager) -> None:
        """Test getting an existing room."""
        room_id = TEST_ROOM_ID

        # Room doesn't exist yet
        assert room_manager.get_room(room_id) is None

        # Create room
        room_manager.get_or_create_room(room_id)

        # Now it should exist
        room = room_manager.get_room(room_id)
        assert room is not None
        assert room.room_id == room_id

    async def test_remove_room(self, room_manager: RoomManager) -> None:
        """Test removing a room."""
        room_id = TEST_ROOM_ID
        room_manager.get_or_create_room(room_id)

        assert len(room_manager.rooms) == 1

        await room_manager.remove_room(room_id)
        assert len(room_manager.rooms) == 0


class TestIdlePlayerDetection:
    """Test suite for idle player detection."""

    async def test_idle_check_only_during_active_game(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test that idle check only runs during active game phases."""
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

        # In lobby phase, no idle checks
        game_room.metadata.game_phase = GamePhase.LOBBY
        await game_room.check_idle_players()
        assert PLAYER_ONE_ID in game_room.players

        # In complete phase, no idle checks
        game_room.metadata.game_phase = GamePhase.FINAL_RESULTS
        await game_room.check_idle_players()
        assert PLAYER_ONE_ID in game_room.players

    async def test_idle_player_detection(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test detecting and disconnecting idle players."""
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

        # Set game to active phase
        game_room.metadata.game_phase = GamePhase.DRAWING

        # Simulate old activity (past idle_timeout_seconds)
        old_time = time.time() - (settings.idle_timeout_seconds + 60)
        game_room.players[PLAYER_ONE_ID].last_activity = old_time

        # Check for idle players
        await game_room.check_idle_players()

        # Player should be disconnected
        assert mock_websocket.close_calls == [{"code": 1000, "reason": "Disconnected due to inactivity"}]

    async def test_active_player_not_disconnected(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test that active players are not disconnected."""
        await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

        game_room.metadata.game_phase = GamePhase.DRAWING

        # Update activity to now
        game_room.update_player_activity(PLAYER_ONE_ID)

        # Check for idle players
        await game_room.check_idle_players()

        # Player should still be connected
        assert PLAYER_ONE_ID in game_room.players
        assert mock_websocket.close_calls == []


class TestRoomTaskScheduler:
    """Regression tests for RoomTaskScheduler lifecycle."""

    async def test_shutdown_clears_every_task_slot(self, game_room: GameRoom) -> None:
        """shutdown() must cancel every timer this scheduler owns."""
        scheduler = game_room.scheduler

        scheduler.schedule_guessing_start(30)
        scheduler.schedule_next_round(5, round_number=2)
        scheduler.schedule_scoring_timeout(30)
        scheduler.schedule_game_complete()

        tasks = _scheduler_tasks(scheduler)
        assert tasks["_guessing_start_task"] is not None
        assert tasks["_next_round_start_task"] is not None
        assert tasks["_round_scoring_task"] is not None
        assert tasks["_game_complete_task"] is not None

        await scheduler.shutdown()

        tasks = _scheduler_tasks(scheduler)
        assert tasks["_idle_check_task"] is None
        assert tasks["_guessing_start_task"] is None
        assert tasks["_next_round_start_task"] is None
        assert tasks["_round_scoring_task"] is None
        assert tasks["_game_complete_task"] is None

    async def test_cancel_round_tasks_preserves_idle_check(self, game_room: GameRoom) -> None:
        """cancel_round_tasks() must not touch the idle-check loop."""
        scheduler = game_room.scheduler
        scheduler.start_idle_check()
        scheduler.schedule_guessing_start(30)

        scheduler.cancel_round_tasks()

        tasks = _scheduler_tasks(scheduler)
        assert tasks["_guessing_start_task"] is None
        assert tasks["_idle_check_task"] is not None


class TestRobustGuessScoring:
    """Scoring must stay correct across mid-guessing disconnects/reconnects."""

    async def test_start_guessing_is_idempotent(self, room_with_players: GameRoom) -> None:
        """A second start_guessing (e.g. late scheduler fire) must not reassign targets."""
        room_with_players.start_guessing()
        original_targets = dict(room_with_players.metadata.guess_targets)

        room_with_players.start_guessing()

        assert room_with_players.metadata.guess_targets == original_targets

    async def test_host_submit_alone_does_not_score(self, room_with_players: GameRoom) -> None:
        """With both players connected, one submission is not all submissions (bug a)."""
        room_with_players.start_guessing()
        targets = room_with_players.metadata.guess_targets

        scored = rounds.record_guess_submission(
            room_with_players,
            player_id=PLAYER_ONE_ID,
            target_player_id=targets[PLAYER_ONE_ID],
            guesses=["cat"],
        )

        assert scored is False
        assert not rounds.all_expected_guesses_submitted(room_with_players)

    async def test_both_submit_scores(self, room_with_players: GameRoom) -> None:
        """The second of two connected players submitting triggers scoring (bug b)."""
        room_with_players.start_guessing()
        targets = room_with_players.metadata.guess_targets
        rounds.record_guess_submission(
            room_with_players,
            player_id=PLAYER_ONE_ID,
            target_player_id=targets[PLAYER_ONE_ID],
            guesses=["cat"],
        )

        scored = rounds.record_guess_submission(
            room_with_players,
            player_id=PLAYER_TWO_ID,
            target_player_id=targets[PLAYER_TWO_ID],
            guesses=["dog"],
        )

        assert scored is True

    async def test_departed_non_submitter_is_not_expected(self, room_with_players: GameRoom) -> None:
        """If the only non-submitter leaves, the remaining submissions count as complete."""
        room_with_players.start_guessing()
        targets = room_with_players.metadata.guess_targets
        rounds.record_guess_submission(
            room_with_players,
            player_id=PLAYER_ONE_ID,
            target_player_id=targets[PLAYER_ONE_ID],
            guesses=["cat"],
        )

        # player-2 disconnects without submitting -> no longer expected.
        room_with_players.players.pop(PLAYER_TWO_ID)

        assert rounds.all_expected_guesses_submitted(room_with_players)


class TestPresence:
    """Disconnect keeps players as a 'reconnecting' presence during a game."""

    async def test_disconnect_marks_reconnecting_during_game(self, room_with_players: GameRoom) -> None:
        """A mid-game drop marks the player disconnected but keeps them in the room."""
        room_with_players.metadata.game_phase = GamePhase.DRAWING

        await room_with_players.disconnect_player(PLAYER_ONE_ID)

        assert PLAYER_ONE_ID in room_with_players.players
        assert room_with_players.players[PLAYER_ONE_ID].connected is False

    async def test_disconnect_removes_in_lobby(self, room_with_players: GameRoom) -> None:
        """A drop in the lobby removes the player outright."""
        # room_with_players is in the default LOBBY phase.
        await room_with_players.disconnect_player(PLAYER_TWO_ID)

        assert PLAYER_TWO_ID not in room_with_players.players

    async def test_scoring_excludes_disconnected_player(self, room_with_players: GameRoom) -> None:
        """A disconnected player isn't expected to submit, so others complete the round."""
        room_with_players.start_guessing()
        targets = room_with_players.metadata.guess_targets
        room_with_players.players[PLAYER_TWO_ID].connected = False

        scored = rounds.record_guess_submission(
            room_with_players,
            player_id=PLAYER_ONE_ID,
            target_player_id=targets[PLAYER_ONE_ID],
            guesses=["cat"],
        )

        # player-2 is disconnected and therefore not expected, so player-1 alone completes.
        assert scored is True

    async def test_prune_disconnected_removes_only_disconnected(self, room_with_players: GameRoom) -> None:
        """Pruning drops disconnected players and keeps connected ones."""
        room_with_players.players[PLAYER_TWO_ID].connected = False

        await room_with_players.prune_disconnected()

        assert PLAYER_ONE_ID in room_with_players.players
        assert PLAYER_TWO_ID not in room_with_players.players


class TestReviewRegressions:
    """Regression tests for the presence/reconnection code-review fixes."""

    @staticmethod
    def _card(category_id: int) -> PlayerPromptAssignmentState:
        return PlayerPromptAssignmentState(
            category_id=category_id,
            category="Animals",
            item_ids=[1, 2],
            items=["cat", "dog"],
        )

    async def test_remove_player_clears_participant_state(self, room_with_players: GameRoom) -> None:
        """A removed player is forgotten as a participant so they cannot rejoin the round (F1)."""
        room_with_players.start_round(
            round_number=1,
            cards={PLAYER_ONE_ID: self._card(1), PLAYER_TWO_ID: self._card(2)},
        )
        assert PLAYER_TWO_ID in room_with_players.metadata.player_assignments

        await room_with_players.remove_player(PLAYER_TWO_ID)

        # The rejoin gate keys on player_assignments; clearing it blocks a re-join.
        assert PLAYER_TWO_ID not in room_with_players.metadata.player_assignments
        assert PLAYER_TWO_ID not in room_with_players.metadata.player_seats

    async def test_required_votes_ignores_disconnected_players(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """A disconnected player must not inflate the kick-vote threshold (F2)."""
        for pid, name in (
            (PLAYER_ONE_ID, PLAYER_ONE_NAME),
            (PLAYER_TWO_ID, PLAYER_TWO_NAME),
            (PLAYER_THREE_ID, PLAYER_THREE_NAME),
            (PLAYER_FOUR_ID, PLAYER_FOUR_NAME),
        ):
            await game_room.add_player(pid, name, as_websocket(make_ws()))

        required_all_connected = get_required_votes(game_room, target_is_host=False)
        game_room.players[PLAYER_FOUR_ID].connected = False
        required_one_disconnected = get_required_votes(game_room, target_is_host=False)

        assert required_all_connected == 3  # 4 players -> eligible 3 -> ceil 2/3 + 1
        assert required_one_disconnected == 2  # 3 connected -> eligible 2 -> reachable

    async def test_scoring_is_idempotent_outside_guessing(self, room_with_players: GameRoom) -> None:
        """A second scoring trigger after the round already scored is a no-op (F3)."""
        room_with_players.start_guessing()
        room_with_players.metadata.game_phase = GamePhase.ROUND_RESULTS
        room_with_players.metadata.player_scores = {PLAYER_ONE_ID: 50, PLAYER_TWO_ID: 10}

        # Phase is no longer GUESSING, so the locked scorer must bail before re-scoring
        # (and before touching the database).
        await room_with_players.score_and_broadcast_round()

        assert room_with_players.metadata.player_scores == {PLAYER_ONE_ID: 50, PLAYER_TWO_ID: 10}

    async def test_all_connected_players_ready_ignores_disconnected(self, room_with_players: GameRoom) -> None:
        """Early drawing->guessing fires once every *connected* player is ready (F5)."""
        room_with_players.metadata.game_phase = GamePhase.DRAWING
        room_with_players.players[PLAYER_TWO_ID].connected = False
        room_with_players.mark_player_ready(PLAYER_ONE_ID)

        assert rounds.all_connected_players_ready(room_with_players) is True

    async def test_room_state_card_keeps_ids_for_rejoiner(self, room_with_players: GameRoom) -> None:
        """The reconnect snapshot's card must keep categoryId/itemIds, not drop them (F6)."""
        room_with_players.start_round(
            round_number=1,
            cards={PLAYER_ONE_ID: self._card(7), PLAYER_TWO_ID: self._card(8)},
        )

        state = room_with_players.room_state_event(for_player_id=PLAYER_ONE_ID)

        assert state.card is not None
        assert state.card.category_id == 7
        assert state.card.item_ids == [1, 2]

    async def test_start_guessing_excludes_disconnected_from_targets(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """A disconnected player is not assigned a drawing to guess (F7)."""
        for pid, name in (
            (PLAYER_ONE_ID, PLAYER_ONE_NAME),
            (PLAYER_TWO_ID, PLAYER_TWO_NAME),
            (PLAYER_THREE_ID, PLAYER_THREE_NAME),
        ):
            await game_room.add_player(pid, name, as_websocket(make_ws()))
        game_room.players[PLAYER_THREE_ID].connected = False

        game_room.start_guessing()

        assert PLAYER_THREE_ID not in game_room.metadata.guess_targets
        assert PLAYER_ONE_ID in game_room.metadata.guess_targets
        assert PLAYER_TWO_ID in game_room.metadata.guess_targets
