"""Tests for game room management functionality."""

import json
import time
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.categories import service as category_service
from app.core.types import GamePhase
from app.rooms.manager import GameRoom, PlayerInfo
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState


class TestGameRoom:
    """Test suite for GameRoom class."""

    async def test_create_room(self, room_id) -> None:
        """Test creating a new game room."""
        room = GameRoom(room_id)
        assert room.room_id == room_id
        assert len(room.players) == 0
        assert room.host_id is None
        assert room.metadata.game_phase == GamePhase.LOBBY

    async def test_add_first_player_becomes_host(self, game_room, mock_websocket) -> None:
        """Test that the first player to join becomes the host."""
        player_id = "player-1"
        player_name = "Alice"

        await game_room.add_player(player_id, player_name, mock_websocket)

        assert len(game_room.players) == 1
        assert game_room.host_id == player_id
        assert game_room.players[player_id].name == player_name

    async def test_add_multiple_players(self, game_room, make_ws) -> None:
        """Test adding multiple players to a room."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)
        await game_room.add_player("player-3", "Charlie", ws3)

        assert len(game_room.players) == 3
        assert game_room.host_id == "player-1"  # First player is host

    async def test_remove_player(self, game_room, mock_websocket) -> None:
        """Test removing a player from the room."""
        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert len(game_room.players) == 1

        await game_room.remove_player("player-1")
        assert len(game_room.players) == 0

    async def test_host_transfer_on_host_leave(self, game_room, make_ws, monkeypatch) -> None:
        """Test that host is transferred when the host leaves."""
        ws1, ws2 = make_ws(), make_ws()
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 0)

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)

        assert game_room.host_id == "player-1"

        await game_room.remove_player("player-1")
        assert game_room._pending_host_transfer is not None
        await game_room._pending_host_transfer

        assert game_room.host_id == "player-2"

        # Verify the host_changed message content was broadcast to Bob
        messages = [json.loads(message) for message in ws2.sent_texts]
        host_changed = next((m for m in messages if m.get("type") == "host_changed"), None)
        assert host_changed is not None
        assert host_changed["newHostId"] == "player-2"

    async def test_no_host_when_room_empty(self, game_room, mock_websocket) -> None:
        """Test that host_id is None when all players leave."""
        await game_room.add_player("player-1", "Alice", mock_websocket)
        await game_room.remove_player("player-1")

        assert game_room.host_id is None
        assert len(game_room.players) == 0

    async def test_update_player_activity(self, game_room, mock_websocket) -> None:
        """Test updating player's last activity timestamp."""
        with patch("app.rooms.manager.time.time", side_effect=[1000.0, 1000.0, 1001.0]):
            await game_room.add_player("player-1", "Alice", mock_websocket)
            initial_time = game_room.players["player-1"].last_activity

            game_room.update_player_activity("player-1")
            updated_time = game_room.players["player-1"].last_activity

        assert updated_time > initial_time

    async def test_broadcast_to_all_players(self, room_with_players) -> None:
        """Test broadcasting a message to all players."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.broadcast(message)

        for player in room_with_players.players.values():
            assert player.websocket.sent_texts == [json.dumps(message)]

    async def test_broadcast_exclude_player(self, room_with_players) -> None:
        """Test broadcasting with exclusion."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.broadcast(message, exclude="player-1")

        player1 = room_with_players.players["player-1"]
        player2 = room_with_players.players["player-2"]

        assert player1.websocket.sent_texts == []
        assert player2.websocket.sent_texts == [json.dumps(message)]

    async def test_send_to_specific_player(self, room_with_players) -> None:
        """Test sending a message to a specific player."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.send_to_player("player-1", message)

        player1 = room_with_players.players["player-1"]
        player2 = room_with_players.players["player-2"]

        assert player1.websocket.sent_texts == [json.dumps(message)]
        assert player2.websocket.sent_texts == []

    async def test_get_player_list(self, room_with_players) -> None:
        """Test getting the list of players."""
        player_list = room_with_players.get_player_list()

        assert len(player_list) == 2
        assert {"id": "player-1", "name": "Alice"} in player_list
        assert {"id": "player-2", "name": "Bob"} in player_list

    async def test_is_empty(self, game_room, mock_websocket) -> None:
        """Test checking if room is empty."""
        assert game_room.is_empty() is True

        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert game_room.is_empty() is False

        await game_room.remove_player("player-1")
        assert game_room.is_empty() is True

    async def test_metadata_initialization(self, game_room) -> None:
        """Test that room metadata is properly initialized."""
        assert game_room.metadata.game_phase == GamePhase.LOBBY
        assert game_room.metadata.difficulty == "medium"
        assert game_room.metadata.max_rounds == 5
        assert game_room.metadata.pad_visibility is True
        assert len(game_room.metadata.ready_players) == 0

    async def test_ready_players_tracking(self, room_with_players) -> None:
        """Test tracking ready players."""
        assert len(room_with_players.metadata.ready_players) == 0

        room_with_players.metadata.ready_players.add("player-1")
        assert len(room_with_players.metadata.ready_players) == 1

        room_with_players.metadata.ready_players.add("player-2")
        assert len(room_with_players.metadata.ready_players) == 2

    async def test_mark_player_ready_returns_ready_status_payload(self, room_with_players) -> None:
        """Test ready-state payload serialization uses websocket aliases."""
        payload = room_with_players.mark_player_ready("player-1")

        assert payload.model_dump(by_alias=True, exclude_none=True) == {
            "type": "ready_status",
            "readyCount": 1,
            "totalPlayers": 2,
        }

    async def test_start_guessing_resets_ready_players_and_sets_timestamp(self, room_with_players) -> None:
        """Guessing starts with a fresh ready state and an explicit phase start time."""
        room_with_players.metadata.ready_players.update({"player-1", "player-2"})

        timeout_seconds = room_with_players.start_guessing()

        assert timeout_seconds == 60
        assert room_with_players.metadata.game_phase == GamePhase.GUESSING
        assert room_with_players.metadata.ready_players == set()
        assert room_with_players.metadata.guessing_start_time is not None

    async def test_broadcast_handles_disconnected_player(self, game_room, make_ws) -> None:
        """Test that broadcast handles disconnected players gracefully."""
        ws1 = make_ws()
        ws2 = make_ws(send_error=Exception("Connection closed"))

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)

        message = {"type": "test"}
        await game_room.broadcast(message)

        # Player 2 should be removed due to error
        assert "player-2" not in game_room.players
        assert "player-1" in game_room.players

    async def test_room_marked_empty_after_all_disconnect(self, game_room, mock_websocket) -> None:
        """Test that room is marked as empty after all players disconnect.

        Note: rooms are not immediately removed — the periodic cleanup loop
        handles hibernation (1 min) and removal (5 min).
        """
        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert not game_room.is_empty()

        await game_room.remove_player("player-1")

        assert game_room.is_empty()
        assert game_room._emptied_at is not None

    async def test_start_round_with_server_cards_recovers_when_categories_missing(self, make_ws, monkeypatch) -> None:
        """Test that the round task does not crash when no matching categories exist."""
        room = GameRoom("ROOM-NO-CATEGORIES")
        room.players["player-1"] = PlayerInfo(id="player-1", name="Alice", websocket=make_ws())
        room.players["player-2"] = PlayerInfo(id="player-2", name="Bob", websocket=make_ws())
        room.broadcast = AsyncMock()
        room.persist = AsyncMock()

        monkeypatch.setattr(
            category_service,
            "select_category_sets",
            AsyncMock(side_effect=HTTPException(status_code=404, detail="No categories found for difficulty: medium")),
        )

        await room.start_round_with_server_cards()

        assert room.metadata.game_phase == GamePhase.LOBBY
        room.broadcast.assert_awaited_once()
        assert room.broadcast.await_args.args[0].type == "room_state"
        room.persist.assert_awaited_once()

    async def test_initiate_kick_vote_broadcasts_modeled_payload(self, game_room, make_ws) -> None:
        """Test kick vote start broadcast preserves the expected protocol shape."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)
        await game_room.add_player("player-3", "Charlie", ws3)

        result = await game_room.initiate_kick_vote("player-2", "player-1")

        assert result.success is True
        assert result.vote_id == "player-1"
        messages = [json.loads(message) for message in ws1.sent_texts]
        assert messages[-1]["type"] == "kick_vote_started"
        assert messages[-1]["targetPlayerId"] == "player-1"
        assert messages[-1]["targetPlayerName"] == "Alice"
        assert messages[-1]["initiatorId"] == "player-2"
        assert messages[-1]["currentVotes"] == 1
        assert messages[-1]["requiredVotes"] == 2
        assert "expiresAt" in messages[-1]

    async def test_cast_kick_vote_returns_typed_progress_result(self, game_room, make_ws) -> None:
        """Test kick-vote progress returns a typed result object."""
        ws1, ws2, ws3, ws4 = make_ws(), make_ws(), make_ws(), make_ws()

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)
        await game_room.add_player("player-3", "Charlie", ws3)
        await game_room.add_player("player-4", "Dana", ws4)

        start_result = await game_room.initiate_kick_vote("player-2", "player-1")
        assert start_result.success is True

        vote_result = await game_room.cast_kick_vote("player-3", "player-1")

        assert vote_result.success is True
        assert vote_result.vote_passed is False
        assert vote_result.current_votes == 2
        assert vote_result.required_votes == 3

    async def test_room_state_round_trips_through_persistence_model(self, game_room) -> None:
        """Test persisted room state preserves structured metadata."""
        game_room.host_id = "host-1"
        game_room._last_host_id = "host-1"
        game_room.metadata.game_phase = GamePhase.DRAWING
        game_room.metadata.current_round = 2
        game_room.metadata.ready_players.add("host-1")
        game_room.metadata.submitted_players.add("player-2")
        game_room.metadata.player_assignments = {
            "player-1": PlayerPromptAssignmentState(
                category_id=1,
                category="Animals",
                item_ids=[11, 12],
                items=["cat", "dog"],
                alternatives={"cat": ["kitty"]},
            ),
        }
        game_room.metadata.guess_submissions = [
            GuessSubmissionState(player_id="player-2", target_player_id="player-1", guesses=["cat"]),
        ]

        restored_room = GameRoom.from_state(game_room.to_state())

        assert restored_room.host_id == "host-1"
        assert restored_room.metadata.game_phase == GamePhase.DRAWING
        assert restored_room.metadata.current_round == 2
        assert restored_room.metadata.ready_players == {"host-1"}
        assert restored_room.metadata.submitted_players == {"player-2"}
        assert restored_room.metadata.player_assignments["player-1"].alternatives == {"cat": ["kitty"]}
        assert restored_room.metadata.guess_submissions[0].player_id == "player-2"
        assert restored_room.metadata.guess_submissions[0].guesses == ["cat"]


class TestRoomManager:
    """Test suite for RoomManager class."""

    def test_create_room_manager(self, room_manager) -> None:
        """Test creating a room manager."""
        assert len(room_manager.rooms) == 0

    async def test_get_or_create_room(self, room_manager) -> None:
        """Test getting or creating a room."""
        room_id = "TEST01"

        # First call should create a new room
        room1 = room_manager.get_or_create_room(room_id)
        assert room1.room_id == room_id
        assert len(room_manager.rooms) == 1

        # Second call should return the same room
        room2 = room_manager.get_or_create_room(room_id)
        assert room1 is room2
        assert len(room_manager.rooms) == 1

    async def test_get_room(self, room_manager) -> None:
        """Test getting an existing room."""
        room_id = "TEST01"

        # Room doesn't exist yet
        assert room_manager.get_room(room_id) is None

        # Create room
        room_manager.get_or_create_room(room_id)

        # Now it should exist
        room = room_manager.get_room(room_id)
        assert room is not None
        assert room.room_id == room_id

    async def test_remove_room(self, room_manager) -> None:
        """Test removing a room."""
        room_id = "TEST01"
        room_manager.get_or_create_room(room_id)

        assert len(room_manager.rooms) == 1

        await room_manager.remove_room(room_id)
        assert len(room_manager.rooms) == 0


class TestIdlePlayerDetection:
    """Test suite for idle player detection."""

    async def test_idle_check_only_during_active_game(self, game_room, mock_websocket) -> None:
        """Test that idle check only runs during active game phases."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        # In lobby phase, no idle checks
        game_room.metadata.game_phase = GamePhase.LOBBY
        await game_room._check_idle_players()
        assert "player-1" in game_room.players

        # In complete phase, no idle checks
        game_room.metadata.game_phase = GamePhase.FINAL_RESULTS
        await game_room._check_idle_players()
        assert "player-1" in game_room.players

    async def test_idle_player_detection(self, game_room, mock_websocket) -> None:
        """Test detecting and disconnecting idle players."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        # Set game to active phase
        game_room.metadata.game_phase = GamePhase.DRAWING

        # Simulate old activity (more than 3 minutes ago)
        old_time = time.time() - (4 * 60)  # 4 minutes ago
        game_room.players["player-1"].last_activity = old_time

        # Check for idle players
        await game_room._check_idle_players()

        # Player should be disconnected
        assert mock_websocket.close_calls == [{"code": 1000, "reason": "Disconnected due to inactivity"}]

    async def test_active_player_not_disconnected(self, game_room, mock_websocket) -> None:
        """Test that active players are not disconnected."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        game_room.metadata.game_phase = GamePhase.DRAWING

        # Update activity to now
        game_room.update_player_activity("player-1")

        # Check for idle players
        await game_room._check_idle_players()

        # Player should still be connected
        assert "player-1" in game_room.players
        assert mock_websocket.close_calls == []
