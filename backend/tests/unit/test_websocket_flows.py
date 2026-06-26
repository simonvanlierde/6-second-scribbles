"""Fast websocket flow tests that do not require real Postgres or Redis."""
# spell-checker: ignore VKICK, NOHOSTK

from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING, cast

from app.core.types import GamePhase
from tests.constants import (
    ALICE,
    BOB,
    CHARLIE,
    GAME_IN_PROGRESS,
    HOST_CANNOT_BE_VOTE_KICKED_ERROR,
    JOIN_ERROR,
    KICK_ERROR,
    KICK_VOTE_STARTED,
    KICK_VOTE_UPDATED,
    MEDIUM,
    PLAYER_1,
    PLAYER_2,
    PLAYER_3,
    PLAYER_JOINED,
    PLAYER_KICKED,
    READY_STATUS,
    ROOM_STATE,
    ROUND_COMPLETE,
    START_GAME,
    START_GUESSING,
    START_ROUND,
    VOTE_KICK_PUBLIC_ONLY_ERROR,
)
from tests.helpers import JoinedPlayer, join_player, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from starlette.testclient import WebSocketTestSession


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


def test_server_starts_guessing_after_round_timer(
    test_client: TestClient,
    immediate_guessing_transition: None,
) -> None:
    """Timer expiry transitions the room into guessing automatically."""
    _ = immediate_guessing_transition
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


def test_public_room_player_can_vote_kick_non_host_player(test_client: TestClient) -> None:
    """Non-host players can vote-kick other non-hosts in public rooms."""
    with joined_players(
        test_client,
        "VKICK1",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB), JoinedPlayer(PLAYER_3, CHARLIE)],
    ) as (ws1, ws2, ws3):
        send_json(ws2, {"type": "initiate_kick", "playerId": PLAYER_2, "targetPlayerId": PLAYER_3})

        for ws in (ws1, ws2, ws3):
            started = receive_json(ws)
            assert started["type"] == KICK_VOTE_STARTED
            assert started["targetPlayerId"] == PLAYER_3

        send_json(ws1, {"type": "cast_kick_vote", "playerId": PLAYER_1, "targetPlayerId": PLAYER_3})

        ws1_messages = [receive_json(ws1), receive_json(ws1)]
        assert [message["type"] for message in ws1_messages] == [KICK_VOTE_UPDATED, PLAYER_KICKED]
        assert ws1_messages[1]["playerId"] == PLAYER_3

        ws2_messages = [receive_json(ws2), receive_json(ws2)]
        assert [message["type"] for message in ws2_messages] == [KICK_VOTE_UPDATED, PLAYER_KICKED]


def test_public_room_players_cannot_vote_kick_the_host(test_client: TestClient) -> None:
    """Host removal is not part of the public-room vote flow."""
    with joined_players(
        test_client,
        "NOHOSTK",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "initiate_kick", "playerId": PLAYER_2, "targetPlayerId": PLAYER_1})

        assert receive_json(ws2) == {
            "type": KICK_ERROR,
            "error": HOST_CANNOT_BE_VOTE_KICKED_ERROR,
            "message": "",
        }


def test_private_room_players_cannot_start_vote_kick(test_client: TestClient) -> None:
    """Vote-kick is hidden and rejected for private rooms."""
    with joined_players(
        test_client,
        "PRIVATE",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB), JoinedPlayer(PLAYER_3, CHARLIE)],
    ) as (ws1, ws2, _ws3):
        send_json(ws1, {"type": "privacy_changed", "isPrivate": True})
        send_json(ws2, {"type": "initiate_kick", "playerId": PLAYER_2, "targetPlayerId": PLAYER_3})

        assert receive_json(ws2) == {
            "type": KICK_ERROR,
            "error": VOTE_KICK_PUBLIC_ONLY_ERROR,
            "message": "",
        }


def test_reconnecting_player_can_rejoin_same_room(test_client: TestClient) -> None:
    """A reconnecting player can rejoin the same room."""
    room_id = "RECONNECT01"

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        receive_json(websocket)
        join_player(websocket, "p1", "Alice")

    with test_client.websocket_connect(f"/ws/{room_id}") as websocket:
        assert receive_json(websocket)["type"] == ROOM_STATE
        assert join_player(websocket, PLAYER_1, ALICE)["type"] == PLAYER_JOINED


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
            send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 3, "drawingTimeLimit": 60})
            assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == [START_GAME, START_GAME]


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

        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 10})
        for ws in (ws1, ws2, ws3):
            assert receive_json(ws)["type"] == START_GAME

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

        for ws in (ws1, ws2, ws3):
            msg = receive_json(ws)
            assert msg["type"] == ROUND_COMPLETE
            assert len(cast("dict[str, object]", msg["scores"])) == 3


def test_join_blocked_during_active_drawing_round(test_client: TestClient) -> None:
    """Joining while a drawing round is active is rejected."""
    room_id = "RECONNECT_MID_GAME"

    with joined_players(
        test_client,
        room_id,
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 60})
        assert receive_json(ws1)["type"] == START_GAME
        assert receive_json(ws2)["type"] == START_GAME

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
        assert receive_json(ws2)["type"] == START_ROUND

    with test_client.websocket_connect(f"/ws/{room_id}") as ws_late:
        initial_state = receive_json(ws_late)
        assert initial_state["type"] == ROOM_STATE
        assert initial_state["gamePhase"] == GamePhase.DRAWING.value

        join_response = join_player(ws_late, "p3", "Charlie")
        assert join_response["type"] == JOIN_ERROR
        assert join_response["error"] == GAME_IN_PROGRESS


def test_round_complete_includes_highlights(test_client: TestClient) -> None:
    """The round-complete payload carries computed highlights, broadcast identically."""
    with joined_players(
        test_client,
        "HIGHLIGHT01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 10})
        receive_json(ws1)
        receive_json(ws2)

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
        receive_json(ws1)
        receive_json(ws2)

        send_json(ws1, {"type": "player_ready", "playerId": PLAYER_1})
        receive_json(ws1)
        receive_json(ws2)
        send_json(ws2, {"type": "player_ready", "playerId": PLAYER_2})
        # Drain the ready + start_guessing broadcasts for both clients.
        for _ in range(4):
            receive_json(ws1)
        for _ in range(4):
            receive_json(ws2)

        send_json(ws1, {"type": "submit_guess", "playerId": PLAYER_1, "targetPlayerId": PLAYER_2, "guesses": ["x"]})
        send_json(ws2, {"type": "submit_guess", "playerId": PLAYER_2, "targetPlayerId": PLAYER_1, "guesses": ["y"]})

        round_complete = (receive_json(ws1), receive_json(ws2))
        assert round_complete[0]["type"] == ROUND_COMPLETE
        assert round_complete[0]["highlights"] == round_complete[1]["highlights"]

        highlights = round_complete[0]["highlights"]
        assert highlights is not None
        # Both players submitted non-empty guesses, so a speed demon is always present.
        assert highlights["speedDemon"]["playerId"] == PLAYER_1


def test_reaction_send_broadcasts_to_all_players(test_client: TestClient) -> None:
    """A reaction is echoed to every player in the room, including the sender."""
    reaction_key = "laugh"
    reaction_received = "reaction_received"
    with joined_players(
        test_client,
        "REACT01",
        [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "reaction_send", "drawingId": PLAYER_2, "reactionKey": reaction_key})

        for socket in (ws1, ws2):
            message = receive_json(socket)
            assert message["type"] == reaction_received
            assert message["drawingId"] == PLAYER_2
            assert message["reactionKey"] == reaction_key
            assert message["senderId"] == PLAYER_1
