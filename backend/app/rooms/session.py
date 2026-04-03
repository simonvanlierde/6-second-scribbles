"""WebSocket session handling for game rooms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from app.rooms.actions import (
    dispatch_event,
    handle_disconnect,
)
from app.rooms.protocol import (
    JOIN_EVENT_TYPE,
    ProtocolErrorEvent,
    parse_client_event,
    send_ws_message,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.rooms.manager import GameRoom

logger = logging.getLogger(__name__)

type ErrorEventType = Literal[
    "protocol_error",
    "permission_error",
    "player_ready_error",
    "submit_guess_error",
    "join_error",
    "kick_error",
]


class RoomWebSocketSession:
    """Own a single accepted websocket connection for a room."""

    def __init__(self, room: GameRoom, websocket: WebSocket) -> None:
        self.room = room
        self.websocket = websocket
        self.player_id: str | None = None

    async def run(self) -> None:
        """Send the initial snapshot, then process messages until disconnect."""
        await send_ws_message(self.websocket, self.room.room_state_event())

        while True:
            payload = await self.websocket.receive_text()
            await self.handle(payload)

    async def handle(self, payload: object) -> None:
        """Parse one inbound message and dispatch it."""
        try:
            event = parse_client_event(payload)
            if event.type != JOIN_EVENT_TYPE and self.player_id:
                self.room.update_player_activity(self.player_id)
            await dispatch_event(self, event)
        except (ValidationError, TypeError, ValueError) as exc:
            logger.info("[Server] Rejected malformed websocket payload: %s", exc)
            await self.send_error("protocol_error", "invalid_payload", "Invalid websocket payload.")
        except Exception:
            logger.exception("[Server] Error processing websocket message")

    async def on_disconnect(self) -> None:
        """Remove the session player from the room and broadcast departure."""
        await handle_disconnect(self)

    def is_host(self) -> bool:
        """Return whether this connection currently belongs to the host."""
        return self.room.is_host(self.player_id)

    async def send_error(self, event_type: ErrorEventType, error: str, message: str) -> None:
        """Send a recoverable protocol error without closing the connection."""
        await send_ws_message(
            self.websocket,
            ProtocolErrorEvent(type=event_type, error=error, message=message),
        )
