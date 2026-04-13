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
    from starlette.testclient import WebSocketTestSession


@pytest.mark.integration
def test_full_game_flow(test_client) -> None:
    with joined_players(
        test_client,
        "GAME01",
        [JoinedPlayer("p1", "Alice"), JoinedPlayer("p2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "start_game", "difficulty": "medium", "rounds": 1, "drawingTimeLimit": 10})
        start_messages = (receive_json(ws1), receive_json(ws2))
        assert [message["type"] for message in start_messages] == ["start_game", "start_game"]

        send_json(
            ws1,
            {
                "type": "start_round",
                "round": 1,
                "cards": {
                    "p1": {"category": "Animals", "items": ["cat", "dog"]},
                    "p2": {"category": "Foods", "items": ["pizza", "burger"]},
                },
            },
        )
        round_messages = (receive_json(ws1), receive_json(ws2))
        assert round_messages[0]["type"] == "start_round"
        assert round_messages[1]["type"] == "start_round"
        assert round_messages[0]["roundStartTime"] > 0

        send_json(
            ws1,
            {
                "type": "draw_stroke",
                "playerId": "p1",
                "stroke": {"color": "#000", "width": 2, "points": [{"x": 10, "y": 20}]},
            },
        )
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["draw_stroke", "draw_stroke"]

        send_json(ws1, {"type": "player_ready", "playerId": "p1"})
        ready_messages = (receive_json(ws1), receive_json(ws2))
        assert ready_messages[0] == {"type": "ready_status", "readyCount": 1, "totalPlayers": 2}
        assert ready_messages[1] == {"type": "ready_status", "readyCount": 1, "totalPlayers": 2}

        send_json(ws2, {"type": "player_ready", "playerId": "p2"})
        ready_then_guessing = [receive_json(ws1), receive_json(ws1), receive_json(ws2), receive_json(ws2)]
        assert [message["type"] for message in ready_then_guessing].count("ready_status") == 2
        assert [message["type"] for message in ready_then_guessing].count("start_guessing") == 2

        send_json(
            ws1,
            {
                "type": "submit_guess",
                "playerId": "p1",
                "targetPlayerId": "p2",
                "guesses": ["pizza", "burger"],
            },
        )
        send_json(
            ws2,
            {
                "type": "submit_guess",
                "playerId": "p2",
                "targetPlayerId": "p1",
                "guesses": ["cat", "dog"],
            },
        )

        round_complete = (receive_json(ws1), receive_json(ws2))
        assert round_complete[0]["type"] == "round_complete"
        assert round_complete[1]["type"] == "round_complete"
        assert round_complete[0]["scores"] == round_complete[1]["scores"]
        assert round_complete[0]["results"] == round_complete[1]["results"]


@pytest.mark.integration
def test_server_starts_guessing_after_round_timer(test_client) -> None:
    with joined_players(
        test_client,
        "AUTO_GUESS_01",
        [JoinedPlayer("p1", "Alice"), JoinedPlayer("p2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "start_game", "difficulty": "medium", "rounds": 1, "drawingTimeLimit": 1})
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["start_game", "start_game"]

        send_json(
            ws1,
            {
                "type": "start_round",
                "round": 1,
                "cards": {
                    "p1": {"category": "Animals", "items": ["cat", "dog"]},
                    "p2": {"category": "Foods", "items": ["pizza", "burger"]},
                },
            },
        )
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["start_round", "start_round"]
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["start_guessing", "start_guessing"]


@pytest.mark.integration
def test_waiting_room_drawpad_controls_are_shared(test_client) -> None:
    with joined_players(
        test_client,
        "DRAW01",
        [JoinedPlayer("p1", "Alice"), JoinedPlayer("p2", "Bob")],
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

        send_json(ws1, {"type": "drawpad_clear", "playerId": "p1"})
        assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == ["drawpad_clear", "drawpad_clear"]


@pytest.mark.integration
def test_non_host_cannot_start_round(test_client) -> None:
    with joined_players(
        test_client,
        "AUTH01",
        [JoinedPlayer("p1", "Alice"), JoinedPlayer("p2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws2, {"type": "start_round", "round": 1, "cards": {}})

        assert receive_json(ws2) == {
            "type": "permission_error",
            "error": "host_only",
            "message": "Only the host can start a round.",
        }

        send_json(ws1, {"type": "request_game_state", "playerId": "p1"})
        room_state = receive_json(ws1)
        assert room_state["type"] == "room_state"
        assert room_state["gamePhase"] == GamePhase.LOBBY.value


@pytest.mark.integration
def test_host_can_kick_non_host_player(test_client) -> None:
    with joined_players(
        test_client,
        "KICK01",
        [JoinedPlayer("p1", "Alice"), JoinedPlayer("p2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "initiate_kick", "playerId": "p1", "targetPlayerId": "p2"})

        host_messages = [receive_json(ws1), receive_json(ws1)]
        host_types = [message["type"] for message in host_messages]
        assert host_types == ["player_kicked", "player_left"]
        assert host_messages[0]["playerId"] == "p2"

        with pytest.raises(WebSocketDisconnect):
            receive_json(ws2)


@pytest.mark.integration
def test_reconnecting_player_can_rejoin_same_room(test_client) -> None:
    room_id = "RECONNECT01"

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        receive_json(websocket)
        join_player(websocket, "p1", "Alice")

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        assert receive_json(websocket)["type"] == "room_state"
        assert join_player(websocket, "p1", "Alice")["type"] == "player_joined"


@pytest.mark.integration
def test_multiple_rooms_can_progress_independently(test_client) -> None:
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
async def test_room_manager_restores_room_state_from_real_redis() -> None:
    room = room_manager.get_or_create_room("REDIS01")
    room.host_id = "host-1"
    room.metadata.game_phase = GamePhase.DRAWING
    room.metadata.current_round = 2
    room.metadata.ready_players.add("host-1")
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
        assert restored_room.host_id == "host-1"
        assert restored_room.metadata.game_phase == GamePhase.DRAWING
        assert restored_room.metadata.current_round == 2
        assert restored_room.metadata.ready_players == {"host-1"}
        assert restored_room.metadata.player_assignments["host-1"].category == "Animals"
        assert restored_room.metadata.guess_submissions[0].player_id == "host-1"
        assert restored_room.metadata.guess_submissions[0].guesses == ["cat"]
    finally:
        await restored_manager.stop()
