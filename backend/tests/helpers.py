"""Shared helpers for websocket-heavy backend tests."""

from __future__ import annotations

import json
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from fastapi.testclient import TestClient
    from starlette.testclient import WebSocketTestSession


@dataclass(frozen=True)
class JoinedPlayer:
    """A player that will join a websocket room during test setup."""

    player_id: str
    name: str


def receive_json(websocket: WebSocketTestSession) -> dict[str, object]:
    """Receive one JSON payload from a websocket session."""
    return json.loads(websocket.receive_text())


def send_json(websocket: WebSocketTestSession, payload: dict[str, object]) -> None:
    """Send one JSON payload to a websocket session."""
    websocket.send_text(json.dumps(payload))


def join_player(websocket: WebSocketTestSession, player_id: str, name: str) -> dict[str, object]:
    """Join a player to a websocket room and return the immediate response."""
    send_json(websocket, {"type": "join", "playerId": player_id, "name": name})
    return receive_json(websocket)


@contextmanager
def joined_players(
    test_client: TestClient,
    room_id: str,
    players: Sequence[JoinedPlayer],
) -> Iterator[tuple[WebSocketTestSession, ...]]:
    """Open websocket sessions and join each player, draining expected join broadcasts."""
    with ExitStack() as stack:
        sockets: list[WebSocketTestSession] = []

        for player in players:
            websocket = stack.enter_context(test_client.websocket_connect(f"/ws/{room_id}"))
            receive_json(websocket)  # initial room_state

            send_json(websocket, {"type": "join", "playerId": player.player_id, "name": player.name})

            for existing_socket in sockets:
                receive_json(existing_socket)
            receive_json(websocket)
            sockets.append(websocket)

        yield tuple(sockets)
