"""Integration tests for end-to-end websocket game flows."""

from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING, cast

import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.types import GamePhase
from app.rooms.manager import RoomManager, room_manager
from app.rooms.state import GuessSubmissionState, PlayerPromptAssignmentState
from tests.helpers import JoinedPlayer, join_player, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from starlette.testclient import WebSocketTestSession

START_GAME = "start_game"
START_ROUND = "start_round"
START_GUESSING = "start_guessing"
ROUND_COMPLETE = "round_complete"
ROOM_STATE = "room_state"
PLAYER_JOINED = "player_joined"
JOIN_ERROR = "join_error"
GAME_IN_PROGRESS = "game_in_progress"
PLAYER_KICKED = "player_kicked"
PLAYER_LEFT = "player_left"
READY_STATUS = "ready_status"
PLAYER_1 = "p1"
PLAYER_2 = "p2"
PLAYER_3 = "p3"
ALICE = "Alice"
BOB = "Bob"
CHARLIE = "Charlie"
MEDIUM = "medium"
HOST_ONE = "host-1"
ANIMALS = "Animals"


@pytest.mark.integration
def test_full_game_flow(test_client: TestClient) -> None:
    """End-to-end game flow covers start, draw, ready, guessing, and scoring."""
    with joined_players(
        test_client,
        "GAME01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 10})
        start_messages = (receive_json(ws1), receive_json(ws2))
        assert [message["type"] for message in start_messages] == [START_GAME, START_GAME]

        send_json(
            ws1,
            {
                "type": START_ROUND,
                "round": 1,
                "cards": {
                    PLAYER_1: {"category": "Animals", "items": ["cat", "dog"]},
                    PLAYER_2: {"category": "Foods", "items": ["pizza", "burger"]},
                },
            },
        )
        round_messages = (receive_json(ws1), receive_json(ws2))
        assert round_messages[0]["type"] == START_ROUND
        assert round_messages[1]["type"] == START_ROUND
        assert cast("int", round_messages[0]["roundStartTime"]) > 0

        send_json(
            ws1,
            {
                "type": "draw_stroke",
                "playerId": "p1",
                "stroke": {"color": "#000", "width": 2, "points": [{"x": 10, "y": 20}]},
            },
        )
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["draw_stroke", "draw_stroke"]

        send_json(ws1, {"type": "player_ready", "playerId": PLAYER_1})
        ready_messages = (receive_json(ws1), receive_json(ws2))
        assert ready_messages[0] == {"type": READY_STATUS, "readyCount": 1, "totalPlayers": 2}
        assert ready_messages[1] == {"type": READY_STATUS, "readyCount": 1, "totalPlayers": 2}

        send_json(ws2, {"type": "player_ready", "playerId": PLAYER_2})
        ready_then_guessing = [receive_json(ws1), receive_json(ws1), receive_json(ws2), receive_json(ws2)]
        assert [message["type"] for message in ready_then_guessing].count(READY_STATUS) == 2
        assert [message["type"] for message in ready_then_guessing].count(START_GUESSING) == 2

        send_json(
            ws1,
            {
                "type": "submit_guess",
                "playerId": PLAYER_1,
                "targetPlayerId": PLAYER_2,
                "guesses": ["pizza", "burger"],
            },
        )
        send_json(
            ws2,
            {
                "type": "submit_guess",
                "playerId": PLAYER_2,
                "targetPlayerId": PLAYER_1,
                "guesses": ["cat", "dog"],
            },
        )

        round_complete = (receive_json(ws1), receive_json(ws2))
        assert round_complete[0]["type"] == ROUND_COMPLETE
        assert round_complete[1]["type"] == ROUND_COMPLETE
        assert round_complete[0]["scores"] == round_complete[1]["scores"]
        assert round_complete[0]["results"] == round_complete[1]["results"]


@pytest.mark.integration
def test_server_starts_guessing_after_round_timer(test_client: TestClient) -> None:
    """Timer expiry transitions the room into guessing automatically."""
    with joined_players(
        test_client,
        "AUTO_GUESS_01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 1})
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == [START_GAME, START_GAME]

        send_json(
            ws1,
            {
                "type": START_ROUND,
                "round": 1,
                "cards": {
                    PLAYER_1: {"category": "Animals", "items": ["cat", "dog"]},
                    PLAYER_2: {"category": "Foods", "items": ["pizza", "burger"]},
                },
            },
        )
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == [START_ROUND, START_ROUND]
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == [START_GUESSING, START_GUESSING]


@pytest.mark.integration
def test_waiting_room_drawpad_controls_are_shared(test_client: TestClient) -> None:
    """Drawpad events fan out to every connected player."""
    with joined_players(
        test_client,
        "DRAW01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(
            ws1,
            {
                "type": "draw_stroke",
                "playerId": "p1",
                "stroke": {
                    "color": "#FF0000",
                    "width": 3,
                    "points": [{"x": 50, "y": 50}, {"x": 100, "y": 100}],
                },
            },
        )
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["draw_stroke", "draw_stroke"]

        send_json(ws1, {"type": "drawpad_clear", "playerId": PLAYER_1})
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["drawpad_clear", "drawpad_clear"]


@pytest.mark.integration
def test_non_host_cannot_start_round(test_client: TestClient) -> None:
    """Only the host can start a round."""
    with joined_players(
        test_client,
        "AUTH01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws2, {"type": START_ROUND, "round": 1, "cards": {}})

        assert receive_json(ws2) == {
            "type": "permission_error",
            "error": "host_only",
            "message": "Only the host can start a round.",
        }

        send_json(ws1, {"type": "request_game_state", "playerId": PLAYER_1})
        room_state = receive_json(ws1)
        assert room_state["type"] == ROOM_STATE
        assert room_state["gamePhase"] == GamePhase.LOBBY.value


@pytest.mark.integration
def test_host_can_kick_non_host_player(test_client: TestClient) -> None:
    """The host can kick another player and the room broadcasts the change."""
    with joined_players(
        test_client,
        "KICK01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "initiate_kick", "playerId": PLAYER_1, "targetPlayerId": PLAYER_2})

        host_messages = [receive_json(ws1), receive_json(ws1)]
        host_types = [message["type"] for message in host_messages]
        assert host_types == [PLAYER_KICKED, PLAYER_LEFT]
        assert host_messages[0]["playerId"] == PLAYER_2

        with pytest.raises(WebSocketDisconnect):
            receive_json(ws2)


@pytest.mark.integration
def test_reconnecting_player_can_rejoin_same_room(test_client: TestClient) -> None:
    """A reconnecting player can rejoin the same room."""
    room_id = "RECONNECT01"

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        receive_json(websocket)
        join_player(websocket, "p1", "Alice")

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        assert receive_json(websocket)["type"] == ROOM_STATE
        assert join_player(websocket, PLAYER_1, ALICE)["type"] == PLAYER_JOINED


@pytest.mark.integration
def test_multiple_rooms_can_progress_independently(test_client: TestClient) -> None:
    """Separate rooms can progress independently."""
    with ExitStack() as stack:
        room_sockets: list[tuple[WebSocketTestSession, WebSocketTestSession]] = []

        for index in range(3):
            room_id = f"CONCURRENT0{index + 1}"
            joined = cast(
                "tuple[WebSocketTestSession, WebSocketTestSession]",
                stack.enter_context(
                    joined_players(
                        test_client,
                        room_id,
                        [
                            JoinedPlayer(f"p{index}-1", f"Player {index}-1"),
                            JoinedPlayer(f"p{index}-2", f"Player {index}-2"),
                        ],
                    )
                ),
            )
            room_sockets.append(joined)

        for ws1, ws2 in room_sockets:
            send_json(ws1, {"type": "start_game", "difficulty": "medium", "rounds": 3, "drawingTimeLimit": 60})
            assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["start_game", "start_game"]


@pytest.mark.integration
def test_three_player_full_round(test_client: TestClient) -> None:
    """Three players complete a full drawing and guessing round together."""
    drawn_items: dict[str, list[str]] = {
        PLAYER_1: ["cat", "dog"],
        PLAYER_2: ["pizza", "burger"],
        PLAYER_3: ["tennis", "soccer"],
    }

    with joined_players(
        test_client,
        "GAME_3P",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB), JoinedPlayer(PLAYER_3, CHARLIE)],
    ) as (ws1, ws2, ws3):
        sockets = {PLAYER_1: ws1, PLAYER_2: ws2, PLAYER_3: ws3}

        # Start game
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 10})
        for ws in (ws1, ws2, ws3):
            assert receive_json(ws)["type"] == START_GAME

        # Host starts round with cards for all 3 players
        send_json(
            ws1,
            {
                "type": START_ROUND,
                "round": 1,
                "cards": {pid: {"category": "Test", "items": items} for pid, items in drawn_items.items()},
            },
        )
        for ws in (ws1, ws2, ws3):
            assert receive_json(ws)["type"] == START_ROUND

        # All 3 players mark ready - each socket receives 3x ready_status + 1x start_guessing
        for pid, ws in sockets.items():
            send_json(ws, {"type": "player_ready", "playerId": pid})

        guess_targets: dict[str, str] = {}
        for ws in (ws1, ws2, ws3):
            msgs = [receive_json(ws) for _ in range(4)]
            types = [m["type"] for m in msgs]
            assert types.count(READY_STATUS) == 3
            assert types.count(START_GUESSING) == 1
            if not guess_targets:
                start_guessing_msg = next(m for m in msgs if m["type"] == START_GUESSING)
                guess_targets = cast("dict[str, str]", start_guessing_msg["guessTargets"])

        assert len(guess_targets) == 3

        # Each player submits correct guesses for their assigned target
        for guesser_id, target_id in guess_targets.items():
            send_json(
                sockets[guesser_id],
                {
                    "type": "submit_guess",
                    "playerId": guesser_id,
                    "targetPlayerId": target_id,
                    "guesses": drawn_items[target_id],
                },
            )

        # All 3 players receive round_complete
        for ws in (ws1, ws2, ws3):
            msg = receive_json(ws)
            assert msg["type"] == ROUND_COMPLETE
            assert len(cast("dict[str, object]", msg["scores"])) == 3


@pytest.mark.integration
def test_join_blocked_during_active_drawing_round(test_client: TestClient) -> None:
    """Joining while a drawing round is active is rejected."""
    """Joining (or reconnecting) is rejected while a drawing round is active.

    This confirms the intentional game mechanic: players cannot enter mid-round.
    They are expected to wait for the lobby or the next round.
    """
    room_id = "RECONNECT_MID_GAME"

    with joined_players(
        test_client,
        room_id,
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, _ws2):
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 60})
        assert receive_json(ws1)["type"] == START_GAME
        assert receive_json(_ws2)["type"] == START_GAME

        send_json(
            ws1,
            {
                "type": START_ROUND,
                "round": 1,
                "cards": {
                    PLAYER_1: {"category": "Animals", "items": ["cat", "dog"]},
                    PLAYER_2: {"category": "Foods", "items": ["pizza", "burger"]},
                },
            },
        )
        assert receive_json(ws1)["type"] == START_ROUND
        assert receive_json(_ws2)["type"] == START_ROUND

    # A new connection attempts to join while game is in DRAWING phase
    with test_client.websocket_connect(f"/ws/{room_id}") as ws_late:
        initial_state = receive_json(ws_late)
        assert initial_state["type"] == ROOM_STATE
        assert initial_state["gamePhase"] == GamePhase.DRAWING.value

        join_response = join_player(ws_late, "p3", "Charlie")
        assert join_response["type"] == JOIN_ERROR
        assert join_response["error"] == GAME_IN_PROGRESS


@pytest.mark.integration
async def test_room_manager_restores_room_state_from_real_redis() -> None:
    """Room state can be restored from Redis."""
    room = room_manager.get_or_create_room("REDIS01")
    room.host_id = HOST_ONE
    room.metadata.game_phase = GamePhase.DRAWING
    room.metadata.current_round = 2
    room.metadata.ready_players.add(HOST_ONE)
    room.metadata.player_assignments = {
        "host-1": PlayerPromptAssignmentState(
            category_id=1,
            category="Animals",
            item_ids=[11, 12],
            items=["cat", "dog"],
            alternatives={"cat": ["kitty"]},
        ),
    }
    room.metadata.guess_submissions = [
        GuessSubmissionState(player_id="host-1", target_player_id="host-1", guesses=["cat"]),
    ]

    await room.persist()

    restored_manager = RoomManager()
    await restored_manager.start()
    try:
        restored_room = restored_manager.get_room("REDIS01")
        assert restored_room is not None
        assert restored_room.host_id == HOST_ONE
        assert restored_room.metadata.game_phase == GamePhase.DRAWING
        assert restored_room.metadata.current_round == 2
        assert restored_room.metadata.ready_players == {HOST_ONE}
        assert restored_room.metadata.player_assignments[HOST_ONE].category == ANIMALS
        assert restored_room.metadata.guess_submissions[0].player_id == HOST_ONE
        assert restored_room.metadata.guess_submissions[0].guesses == ["cat"]
    finally:
        await restored_manager.stop()
