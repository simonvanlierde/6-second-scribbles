"""Tests for game room management functionality."""
# cspell: ignore rejoiner

import asyncio
import json
import random
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.categories import service as category_service
from app.core.config import settings
from app.core.types import GamePhase
from app.rooms import kick_vote, player_lifecycle, rounds
from app.rooms import manager as manager_module
from app.rooms.kick_vote import HOST_CANNOT_BE_VOTE_KICKED_ERROR, VOTE_KICK_PUBLIC_ONLY_ERROR, get_required_votes
from app.rooms.manager import GameRoom, PlayerInfo, RoomManager
from app.rooms.player_lifecycle import ABSENT_BINDING_GRACE_SECONDS, MAX_ABSENT_BINDINGS, SEATS_BUSY_ERROR
from app.rooms.protocol import (
    DrawStrokeBatchServerEvent,
    StrokeDelta,
    StrokeFragment,
    WebSocketMessage,
)
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.constants import (
    HOST_ONE,
    KICK_VOTE_STARTED,
    KICK_VOTE_UPDATED,
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
    ROUND_COMPLETE,
    TEST_ROOM_ID,
)
from tests.support import TestWebSocket, as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable


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

        await player_lifecycle.add_player(game_room, player_id, player_name, as_websocket(mock_websocket))

        assert len(game_room.players) == 1
        assert game_room.host_id == player_id
        assert game_room.players[player_id].name == player_name

    async def test_add_multiple_players(self, game_room: GameRoom, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test adding multiple players to a room."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await player_lifecycle.add_player(game_room, PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))

        assert len(game_room.players) == 3
        assert game_room.host_id == PLAYER_ONE_ID  # First player is host

    async def test_remove_player(self, game_room: GameRoom, mock_websocket: TestWebSocket) -> None:
        """Test removing a player from the room."""
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert len(game_room.players) == 1

        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID)
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

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

        assert game_room.host_id == PLAYER_ONE_ID

        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID)
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
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID)

        assert game_room.host_id is None
        assert len(game_room.players) == 0

    async def test_player_id_cannot_be_claimed_by_another_user(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """A player_id bound to one user rejects a join from a different user."""
        ws_alice, ws_mallory = make_ws(), make_ws()
        await player_lifecycle.add_player(
            game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws_alice), user_id="user-alice"
        )

        with pytest.raises(ValueError, match="identity_conflict"):
            await player_lifecycle.add_player(
                game_room, PLAYER_ONE_ID, "Mallory", as_websocket(ws_mallory), user_id="user-mallory"
            )

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
        await player_lifecycle.add_player(
            game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1), user_id="user-alice"
        )

        # Same user, same player_id, new socket (e.g. a page refresh): must succeed
        # and retain the host role.
        await player_lifecycle.add_player(
            game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws2), user_id="user-alice"
        )

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

        await player_lifecycle.add_player(
            game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws_alice), user_id="user-alice"
        )
        await player_lifecycle.add_player(
            game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws_bob), user_id="user-bob"
        )

        # Host leaves explicitly; a transfer is pending and host_id still lingers.
        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID, forget_identity=True)
        assert game_room.pending_host_transfer is not None

        # Mallory grabs the freed player_id under a different account. She joins as a
        # plain player and must not inherit the lingering host role.
        _player, is_reconnecting_host = await player_lifecycle.add_player(
            game_room,
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
        with patch("app.rooms.manager.time.time", side_effect=[1000.0, 1001.0]):
            await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
            initial_time = game_room.players[PLAYER_ONE_ID].last_activity

            player_lifecycle.update_player_activity(game_room, PLAYER_ONE_ID)
            updated_time = game_room.players[PLAYER_ONE_ID].last_activity

        assert updated_time > initial_time

    async def test_broadcast_to_all_players(self, room_with_players: GameRoom) -> None:
        """Test broadcasting a message to all players."""
        message = cast("WebSocketMessage", {"type": "test", "data": "hello"})

        await room_with_players.broadcast(message)

        for player in room_with_players.players.values():
            assert cast("TestWebSocket", player.websocket).sent_texts == [json.dumps(message, separators=(",", ":"))]

    async def test_broadcast_serializes_once(
        self, room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A broadcast serializes its message once and sends the same text to every player."""
        encode = Mock(wraps=manager_module.encode_ws_message)
        monkeypatch.setattr(manager_module, "encode_ws_message", encode)
        message = cast("WebSocketMessage", {"type": "test", "data": "naïve"})

        await room_with_players.broadcast(message)

        encode.assert_called_once_with(message)
        texts = [cast("TestWebSocket", p.websocket).sent_texts for p in room_with_players.players.values()]
        assert len(texts) > 1
        assert all(t == ['{"type":"test","data":"naïve"}'] for t in texts)

    async def test_broadcast_exclude_player(self, room_with_players: GameRoom) -> None:
        """Test broadcasting with exclusion."""
        message = cast("WebSocketMessage", {"type": "test", "data": "hello"})

        await room_with_players.broadcast(message, exclude=PLAYER_ONE_ID)

        player1 = room_with_players.players[PLAYER_ONE_ID]
        player2 = room_with_players.players[PLAYER_TWO_ID]

        assert cast("TestWebSocket", player1.websocket).sent_texts == []
        assert cast("TestWebSocket", player2.websocket).sent_texts == [json.dumps(message, separators=(",", ":"))]

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

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert not game_room.is_empty()

        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID)
        assert game_room.is_empty()

    async def test_lobby_strokes_reconstructed_and_hydrated(self, game_room: GameRoom) -> None:
        """Partials fold into one authoritative stroke that room_state replays to late joiners."""

        def delta(x: float) -> StrokeDelta:
            return StrokeDelta(color="#000", width=3, points=[x, x])

        # Start a stroke, then two continuation fragments — one growing stroke.
        game_room.apply_lobby_partial("p1", delta(1), is_start=True)
        game_room.apply_lobby_partial("p1", delta(2), is_start=False)
        game_room.apply_lobby_partial("p1", delta(3), is_start=False)
        # A different player's start opens a second stroke.
        game_room.apply_lobby_partial("p2", delta(9), is_start=True)

        assert len(game_room.lobby_strokes) == 2
        assert game_room.lobby_strokes[0].points == [1, 1, 2, 2, 3, 3]

        # A late joiner's snapshot carries the whole doodle, not a blank canvas.
        state = game_room.room_state_event()
        assert len(state.lobby_strokes) == 2

        game_room.clear_lobby_strokes()
        assert game_room.lobby_strokes == []
        assert game_room.room_state_event().lobby_strokes == []

    async def test_lobby_stroke_points_are_capped(self, game_room: GameRoom) -> None:
        """One never-ending stroke can't grow memory past the per-stroke cap."""
        chunk = StrokeDelta(color="#000", width=3, points=[0, 0] * 1000)
        game_room.apply_lobby_partial("p1", chunk, is_start=True)
        for _ in range(10):  # 10k points offered into one stroke
            game_room.apply_lobby_partial("p1", chunk, is_start=False)

        assert len(game_room.lobby_strokes) == 1
        assert len(game_room.lobby_strokes[0].points) == 2 * manager_module.MAX_STROKE_POINTS

    async def test_lobby_point_total_tracks_every_change(
        self, game_room: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The running point total matches the strokes through starts, extensions, trims and clears."""
        monkeypatch.setattr(manager_module, "MAX_LOBBY_POINTS", 50)
        monkeypatch.setattr(manager_module, "MAX_LOBBY_STROKES", 8)
        monkeypatch.setattr(manager_module, "MAX_STROKE_POINTS", 12)
        rng = random.Random(7)  # noqa: S311 - a seeded sequence, not a secret
        new_stroke_share = 0.3
        for step in range(2_000):
            player = f"p{rng.randrange(4)}"
            points = [step, 0] * rng.randrange(1, 6)
            game_room.apply_lobby_partial(
                player, StrokeDelta(color="#000", width=3, points=points), is_start=rng.random() < new_stroke_share
            )
            if step % 500 == 499:
                game_room.clear_lobby_strokes()
            actual = sum(len(stroke.points) // 2 for stroke in game_room.lobby_strokes)
            assert game_room._lobby_points == actual  # noqa: SLF001
            assert actual <= manager_module.MAX_LOBBY_POINTS or len(game_room.lobby_strokes) == 1

    async def test_lobby_fragments_go_out_together_once_per_tick(self, game_room: GameRoom) -> None:
        """Fragments from several players in one tick reach each client as one batch, in order."""
        ws = TestWebSocket()
        game_room.players["p1"] = PlayerInfo(id="p1", name="One", websocket=as_websocket(ws))
        for player_id, x in (("p1", 1), ("p2", 2), ("p1", 3)):
            stroke = StrokeDelta(color="#000", width=3, points=[x, x])
            game_room.queue_lobby_fragment(StrokeFragment(player_id=player_id, stroke=stroke, stroke_start=x == 1))
        assert ws.sent_texts == []

        await asyncio.sleep(manager_module.LOBBY_FRAGMENT_TICK_SECONDS * 2)

        assert len(ws.sent_texts) == 1
        batch = DrawStrokeBatchServerEvent.model_validate_json(ws.sent_texts[0])
        assert [(f.player_id, f.stroke.points[0]) for f in batch.fragments] == [("p1", 1), ("p2", 2), ("p1", 3)]

    async def test_clearing_the_doodle_drops_fragments_waiting_for_the_tick(self, game_room: GameRoom) -> None:
        """A fragment drawn just before a clear does not reappear after it."""
        ws = TestWebSocket()
        game_room.players["p1"] = PlayerInfo(id="p1", name="One", websocket=as_websocket(ws))
        stroke = StrokeDelta(color="#000", width=3, points=[1, 1])
        game_room.queue_lobby_fragment(StrokeFragment(player_id="p1", stroke=stroke, stroke_start=True))

        game_room.clear_lobby_strokes()
        await asyncio.sleep(manager_module.LOBBY_FRAGMENT_TICK_SECONDS * 2)

        assert ws.sent_texts == []

    async def test_a_later_batch_never_overtakes_one_still_going_out(self, game_room: GameRoom) -> None:
        """A player stuck on one batch holds back the next, so everyone gets batches in order."""
        release = asyncio.Event()

        class FirstSendStalls(TestWebSocket):
            calls = 0

            async def send_text(self, message: str) -> None:
                self.calls += 1
                if self.calls == 1:
                    await release.wait()
                await super().send_text(message)

        slow, fast = FirstSendStalls(), TestWebSocket()
        game_room.players["slow"] = PlayerInfo(id="slow", name="Slow", websocket=as_websocket(slow))
        game_room.players["fast"] = PlayerInfo(id="fast", name="Fast", websocket=as_websocket(fast))
        tick = manager_module.LOBBY_FRAGMENT_TICK_SECONDS
        for x in (1, 2):
            stroke = StrokeDelta(color="#000", width=3, points=[x, x])
            game_room.queue_lobby_fragment(StrokeFragment(player_id="p1", stroke=stroke, stroke_start=x == 1))
            await asyncio.sleep(tick * 2)
        assert fast.sent_texts == []  # the second batch waits behind the stalled first

        release.set()
        await asyncio.sleep(tick * 3)

        first_points = [
            DrawStrokeBatchServerEvent.model_validate_json(m).fragments[0].stroke.points[0] for m in fast.sent_texts
        ]
        assert first_points == [1, 2]

    async def test_waiting_for_the_lobby_batch_ends_when_it_has_gone_out(self, game_room: GameRoom) -> None:
        """A clear can wait for a batch in flight, so it never lands before that batch."""
        release = asyncio.Event()

        class Stalls(TestWebSocket):
            async def send_text(self, message: str) -> None:
                await release.wait()
                await super().send_text(message)

        game_room.players["p1"] = PlayerInfo(id="p1", name="One", websocket=as_websocket(Stalls()))
        stroke = StrokeDelta(color="#000", width=3, points=[1, 1])
        game_room.queue_lobby_fragment(StrokeFragment(player_id="p1", stroke=stroke, stroke_start=True))
        await asyncio.sleep(manager_module.LOBBY_FRAGMENT_TICK_SECONDS * 2)

        waiting = asyncio.create_task(game_room.wait_for_lobby_batch())
        await asyncio.sleep(0.01)
        assert not waiting.done()
        release.set()
        await asyncio.wait_for(waiting, timeout=1)

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
        payload = rounds.mark_player_ready(room_with_players, "player-1")

        assert payload.model_dump(by_alias=True, exclude_none=True) == {
            "type": READY_STATUS,
            "readyCount": 1,
            "totalPlayers": 2,
        }

    async def test_start_guessing_resets_ready_players_and_sets_timestamp(self, room_with_players: GameRoom) -> None:
        """Guessing starts with a fresh ready state and an explicit phase start time."""
        room_with_players.metadata.ready_players.update({"player-1", "player-2"})

        timeout_seconds = rounds.start_guessing(room_with_players)

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

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

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
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))
        assert not game_room.is_empty()

        await player_lifecycle.remove_player(game_room, PLAYER_ONE_ID)

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
            "select_category_ids",
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
        monkeypatch.setattr(category_service, "select_category_ids", AsyncMock(return_value=[143, 144]))
        monkeypatch.setattr(
            category_service,
            "deal_category",
            AsyncMock(
                side_effect=lambda _db, *, category_id, **_kwargs: PlayerPromptAssignmentState(
                    category_id=category_id, category="Test", items=["cat"]
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

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await player_lifecycle.add_player(game_room, PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_THREE_ID)

        assert result is None
        messages = [json.loads(message) for message in ws1.sent_texts]
        assert messages[-1]["type"] == KICK_VOTE_STARTED
        assert messages[-1]["targetPlayerId"] == PLAYER_THREE_ID
        assert messages[-1]["targetPlayerName"] == PLAYER_THREE_NAME
        assert messages[-1]["initiatorId"] == PLAYER_TWO_ID
        assert messages[-1]["currentVotes"] == 1
        assert messages[-1]["requiredVotes"] == 2
        assert EXPIRES_AT in messages[-1]

    async def test_cast_kick_vote_broadcasts_progress(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test a non-final kick vote broadcasts the updated tally."""
        ws1, ws2, ws3, ws4 = make_ws(), make_ws(), make_ws(), make_ws()

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await player_lifecycle.add_player(game_room, PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))
        await player_lifecycle.add_player(game_room, PLAYER_FOUR_ID, PLAYER_FOUR_NAME, as_websocket(ws4))

        start_result = await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_FOUR_ID)
        assert start_result is None

        vote_result = await kick_vote.cast_kick_vote(game_room, PLAYER_THREE_ID, PLAYER_FOUR_ID)

        assert vote_result is None
        update = [json.loads(m) for m in ws1.sent_texts if json.loads(m)["type"] == KICK_VOTE_UPDATED][-1]
        assert update["targetPlayerId"] == PLAYER_FOUR_ID
        assert update["currentVotes"] == 2
        assert update["requiredVotes"] == 3
        assert PLAYER_FOUR_ID in game_room.players

    async def test_players_cannot_vote_kick_the_host(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Non-host players must leave rather than vote-kicking the host."""
        ws1, ws2 = make_ws(), make_ws()

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_ONE_ID)

        assert result == HOST_CANNOT_BE_VOTE_KICKED_ERROR

    async def test_players_cannot_vote_kick_in_private_rooms(
        self,
        game_room: GameRoom,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Vote-kick stays reserved for public stranger rooms."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
        await player_lifecycle.add_player(game_room, PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))
        await player_lifecycle.add_player(game_room, PLAYER_THREE_ID, PLAYER_THREE_NAME, as_websocket(ws3))
        game_room.metadata.is_private = True

        result = await kick_vote.initiate_kick_vote(game_room, PLAYER_TWO_ID, PLAYER_THREE_ID)

        assert result == VOTE_KICK_PUBLIC_ONLY_ERROR

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
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

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
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

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
        await player_lifecycle.add_player(game_room, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(mock_websocket))

        game_room.metadata.game_phase = GamePhase.DRAWING

        # Update activity to now
        player_lifecycle.update_player_activity(game_room, PLAYER_ONE_ID)

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

    async def test_final_results_return_to_the_lobby_after_a_delay(
        self, room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The server restarts a finished game on its own, a while after final results."""
        monkeypatch.setattr(settings, "game_complete_delay_seconds", 0)
        monkeypatch.setattr(settings, "final_results_restart_seconds", 0)
        room_with_players.metadata.current_round = 1

        room_with_players.scheduler.schedule_game_complete()
        await asyncio.sleep(0.05)

        assert room_with_players.metadata.game_phase == GamePhase.LOBBY
        socket = cast("TestWebSocket", room_with_players.players[PLAYER_ONE_ID].websocket)
        sent = [json.loads(text)["type"] for text in socket.sent_texts]
        assert sent[-2:] == ["game_complete", "restart_game"]

    async def test_manual_restart_cancels_the_automatic_one(
        self, room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A host restart, or a new game, replaces the pending automatic restart."""
        monkeypatch.setattr(settings, "game_complete_delay_seconds", 0)
        room_with_players.scheduler.schedule_game_complete()
        await asyncio.sleep(0.05)
        assert _scheduler_tasks(room_with_players.scheduler)["_restart_task"] is not None

        rounds.reset_game(room_with_players)

        assert _scheduler_tasks(room_with_players.scheduler)["_restart_task"] is None

    async def test_emptied_room_cancels_the_automatic_restart(
        self, room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nobody is left to restart for once the last player goes."""
        monkeypatch.setattr(settings, "game_complete_delay_seconds", 0)
        room_with_players.scheduler.schedule_game_complete()
        await asyncio.sleep(0.05)

        await player_lifecycle.disconnect_player(room_with_players, PLAYER_ONE_ID)
        assert _scheduler_tasks(room_with_players.scheduler)["_restart_task"] is not None
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_TWO_ID)

        assert _scheduler_tasks(room_with_players.scheduler)["_restart_task"] is None

    async def test_rejoin_after_room_emptied_rearms_the_automatic_restart(
        self,
        room_with_players: GameRoom,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A player back on final results in a room that emptied still returns to the lobby."""
        monkeypatch.setattr(settings, "game_complete_delay_seconds", 0)
        room_with_players.metadata.current_round = 1
        room_with_players.scheduler.schedule_game_complete()
        await asyncio.sleep(0.05)
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_ONE_ID)
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_TWO_ID)

        await player_lifecycle.add_player(room_with_players, PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(make_ws()))

        assert room_with_players.metadata.game_phase == GamePhase.FINAL_RESULTS
        assert room_with_players.scheduler.is_restart_pending()

    async def test_room_emptied_before_game_complete_schedules_no_restart(
        self, room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nobody is left to restart for when the room empties during the final countdown."""
        monkeypatch.setattr(settings, "game_complete_delay_seconds", 0.02)
        room_with_players.metadata.current_round = 1
        room_with_players.metadata.game_phase = GamePhase.ROUND_RESULTS
        room_with_players.scheduler.schedule_game_complete()
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_ONE_ID)
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_TWO_ID)

        await asyncio.sleep(0.1)

        assert not room_with_players.scheduler.is_restart_pending()

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
        rounds.start_guessing(room_with_players)
        original_targets = dict(room_with_players.metadata.guess_targets)

        rounds.start_guessing(room_with_players)

        assert room_with_players.metadata.guess_targets == original_targets

    async def test_host_submit_alone_does_not_score(self, room_with_players: GameRoom) -> None:
        """With both players connected, one submission is not all submissions (bug a)."""
        rounds.start_guessing(room_with_players)
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
        rounds.start_guessing(room_with_players)
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
        rounds.start_guessing(room_with_players)
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

        await player_lifecycle.disconnect_player(room_with_players, PLAYER_ONE_ID)

        assert PLAYER_ONE_ID in room_with_players.players
        assert room_with_players.players[PLAYER_ONE_ID].connected is False

    async def test_disconnect_removes_in_lobby(self, room_with_players: GameRoom) -> None:
        """A drop in the lobby removes the player outright."""
        # room_with_players is in the default LOBBY phase.
        await player_lifecycle.disconnect_player(room_with_players, PLAYER_TWO_ID)

        assert PLAYER_TWO_ID not in room_with_players.players

    async def test_scoring_excludes_disconnected_player(self, room_with_players: GameRoom) -> None:
        """A disconnected player isn't expected to submit, so others complete the round."""
        rounds.start_guessing(room_with_players)
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

        await player_lifecycle.prune_disconnected(room_with_players)

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
        rounds.start_round(
            room_with_players,
            round_number=1,
            cards={PLAYER_ONE_ID: self._card(1), PLAYER_TWO_ID: self._card(2)},
        )
        assert PLAYER_TWO_ID in room_with_players.metadata.player_assignments

        await player_lifecycle.remove_player(room_with_players, PLAYER_TWO_ID)

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
            await player_lifecycle.add_player(game_room, pid, name, as_websocket(make_ws()))

        required_all_connected = get_required_votes(game_room)
        game_room.players[PLAYER_FOUR_ID].connected = False
        required_one_disconnected = get_required_votes(game_room)

        assert required_all_connected == 3  # 4 players -> eligible 3 -> ceil 2/3 + 1
        assert required_one_disconnected == 2  # 3 connected -> eligible 2 -> reachable

    async def test_scoring_is_idempotent_outside_guessing(self, room_with_players: GameRoom) -> None:
        """A second scoring trigger after the round already scored is a no-op (F3)."""
        rounds.start_guessing(room_with_players)
        room_with_players.metadata.game_phase = GamePhase.ROUND_RESULTS
        room_with_players.metadata.player_scores = {PLAYER_ONE_ID: 50, PLAYER_TWO_ID: 10}

        # Phase is no longer GUESSING, so the locked scorer must bail before re-scoring
        # (and before touching the database).
        await room_with_players.score_and_broadcast_round()

        assert room_with_players.metadata.player_scores == {PLAYER_ONE_ID: 50, PLAYER_TWO_ID: 10}

    @staticmethod
    def _round_complete_sent_to(room: GameRoom, player_id: str) -> dict[str, list[dict[str, int]]]:
        sent = cast("TestWebSocket", room.players[player_id].websocket).sent_texts
        return next(msg for msg in map(json.loads, sent) if msg["type"] == ROUND_COMPLETE)

    async def _guessing_round_with_one_submission(self, room: GameRoom) -> None:
        rounds.start_round(room, round_number=1, cards={PLAYER_ONE_ID: self._card(1), PLAYER_TWO_ID: self._card(2)})
        rounds.start_guessing(room)
        room.metadata.guess_submissions = [
            GuessSubmissionState(player_id=PLAYER_ONE_ID, target_player_id=PLAYER_TWO_ID, guesses=["cat"]),
        ]

    async def test_scoring_survives_a_category_removed_mid_round(self, room_with_players: GameRoom) -> None:
        """A reseed that deletes the round's category scores those guesses as 0, not a stuck room."""
        await self._guessing_round_with_one_submission(room_with_players)
        missing = AsyncMock(side_effect=HTTPException(status_code=404, detail="Category not found"))

        with patch.object(category_service, "get_localized_scoring_targets", missing):
            await room_with_players.score_and_broadcast_round()

        assert room_with_players.metadata.game_phase == GamePhase.ROUND_RESULTS
        round_complete = self._round_complete_sent_to(room_with_players, PLAYER_ONE_ID)
        assert round_complete["results"][0]["pointsEarned"] == 0
        assert round_complete["results"][0]["totalItems"] == 0

    async def test_scoring_failure_still_ends_the_round(self, room_with_players: GameRoom) -> None:
        """An unexpected scoring error still broadcasts round_complete and moves the room on."""
        await self._guessing_round_with_one_submission(room_with_players)
        room_with_players.metadata.player_scores = {PLAYER_ONE_ID: 30, PLAYER_TWO_ID: 10}

        with patch.object(rounds, "score_round", AsyncMock(side_effect=RuntimeError("boom"))):
            await room_with_players.score_and_broadcast_round()

        assert room_with_players.metadata.game_phase == GamePhase.ROUND_RESULTS
        round_complete = self._round_complete_sent_to(room_with_players, PLAYER_ONE_ID)
        assert round_complete["results"] == []
        assert round_complete["scores"] == {PLAYER_ONE_ID: 30, PLAYER_TWO_ID: 10}

    async def test_all_connected_players_ready_ignores_disconnected(self, room_with_players: GameRoom) -> None:
        """Early drawing->guessing fires once every *connected* player is ready (F5)."""
        room_with_players.metadata.game_phase = GamePhase.DRAWING
        room_with_players.players[PLAYER_TWO_ID].connected = False
        rounds.mark_player_ready(room_with_players, PLAYER_ONE_ID)

        assert rounds.all_connected_players_ready(room_with_players) is True

    async def test_room_state_card_keeps_ids_for_rejoiner(self, room_with_players: GameRoom) -> None:
        """The reconnect snapshot's card must keep categoryId/itemIds, not drop them (F6)."""
        rounds.start_round(
            room_with_players,
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
            await player_lifecycle.add_player(game_room, pid, name, as_websocket(make_ws()))
        game_room.players[PLAYER_THREE_ID].connected = False

        rounds.start_guessing(game_room)

        assert PLAYER_THREE_ID not in game_room.metadata.guess_targets
        assert PLAYER_ONE_ID in game_room.metadata.guess_targets
        assert PLAYER_TWO_ID in game_room.metadata.guess_targets


async def test_scheduled_round_start_survives_its_own_round_reset(
    make_ws: Callable[..., TestWebSocket],
    monkeypatch: pytest.MonkeyPatch,
    dealt_cards: dict[str, list[str]],
) -> None:
    """The timer task that starts a round must still persist it and arm the guessing timer.

    start_round cancels the round timers, and the round-start task is one of them.
    """
    _ = dealt_cards
    room = GameRoom("SELFCANCEL")
    for player_id, name in ((PLAYER_ONE_ID, PLAYER_ONE_NAME), (PLAYER_TWO_ID, PLAYER_TWO_NAME)):
        room.players[player_id] = PlayerInfo(id=player_id, name=name, websocket=as_websocket(make_ws()))
    persisted: list[GamePhase] = []

    async def persist() -> None:
        await asyncio.sleep(0)  # a real Redis write suspends here
        persisted.append(room.metadata.game_phase)

    monkeypatch.setattr(room, "persist", persist)

    room.scheduler.schedule_next_round(0, round_number=1)
    task = room.scheduler._next_round_start_task  # noqa: SLF001
    assert task is not None
    await asyncio.wait_for(asyncio.shield(task), timeout=2)

    assert persisted == [GamePhase.DRAWING]
    assert room.scheduler._guessing_start_task is not None  # noqa: SLF001
    await room.scheduler.shutdown()


HOST_ID = "host"
FIRST_VISITOR = "visitor-0"
LATECOMER = "latecomer"


async def test_absent_player_bindings_are_bounded(make_ws: Callable[..., TestWebSocket]) -> None:
    """Past MAX_ABSENT_BINDINGS recent departures newcomers wait; once those expire, the earliest go."""
    room = GameRoom("BINDINGS01")
    await player_lifecycle.add_player(room, HOST_ID, "Host", as_websocket(make_ws()), rejoin_key="host-key")
    for i in range(MAX_ABSENT_BINDINGS):
        await player_lifecycle.add_player(
            room, f"visitor-{i}", "Visitor", as_websocket(make_ws()), rejoin_key=f"key-{i}"
        )
        await player_lifecycle.remove_player(room, f"visitor-{i}")

    with pytest.raises(ValueError, match=SEATS_BUSY_ERROR):
        await player_lifecycle.add_player(room, LATECOMER, "Late", as_websocket(make_ws()), rejoin_key="late-key")

    departed_at = room.metadata.player_departed_at
    for pid in departed_at:
        departed_at[pid] -= ABSENT_BINDING_GRACE_SECONDS
    await player_lifecycle.add_player(room, LATECOMER, "Late", as_websocket(make_ws()), rejoin_key="late-key")
    await player_lifecycle.remove_player(room, LATECOMER)

    keys = room.metadata.player_rejoin_keys
    assert HOST_ID in keys
    assert len(keys) == MAX_ABSENT_BINDINGS + 1
    assert LATECOMER in keys
    assert FIRST_VISITOR not in keys
    await room.scheduler.shutdown()
