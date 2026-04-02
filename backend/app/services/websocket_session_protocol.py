"""Protocol for websocket session actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.game_room import GameRoom

type ErrorEventType = Literal[
    "protocol_error",
    "permission_error",
    "player_ready_error",
    "submit_guess_error",
    "join_error",
    "kick_error",
]


class WebSocketSessionContext(Protocol):
    """Minimal interface required by websocket action handlers."""

    room: GameRoom
    websocket: WebSocket
    player_id: str | None

    def is_host(self) -> bool:
        """Return whether this connection currently belongs to the host."""

    async def send_error(self, event_type: ErrorEventType, error: str, message: str) -> None:
        """Send a recoverable protocol error without closing the connection."""
