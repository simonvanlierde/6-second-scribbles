"""Shared lightweight helpers for backend tests: websocket doubles and websocket-session helpers."""

from __future__ import annotations

import json
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from fastapi import WebSocket
    from fastapi.testclient import TestClient
    from starlette.testclient import WebSocketTestSession


@dataclass
class TestWebSocket:
    """Lean websocket test double for room-oriented unit tests."""

    sent_texts: list[str] = field(default_factory=list)
    close_calls: list[dict[str, object | None]] = field(default_factory=list)
    send_error: Exception | None = None

    async def send_text(self, message: str) -> None:
        """Record a websocket text payload."""
        if self.send_error is not None:
            raise self.send_error
        self.sent_texts.append(message)

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        """Record a websocket close call."""
        self.close_calls.append({"code": code, "reason": reason})


def as_websocket(test_websocket: TestWebSocket) -> WebSocket:
    """Cast a lightweight websocket double to the FastAPI websocket type used by GameRoom."""
    return cast("WebSocket", test_websocket)


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


def join_player(
    websocket: WebSocketTestSession, player_id: str, name: str, *, rejoin_key: str | None = None
) -> dict[str, object]:
    """Join a player to a websocket room and return the immediate response."""
    send_json(websocket, {"type": "join", "playerId": player_id, "name": name, "rejoinKey": rejoin_key})
    return receive_json(websocket)


@contextmanager
def joined_players(
    test_client: TestClient,
    room_id: str,
    players: Sequence[JoinedPlayer],
) -> Generator[tuple[WebSocketTestSession, ...]]:
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
