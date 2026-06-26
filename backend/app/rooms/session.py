"""WebSocket session handling for game rooms."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from app.core.config import settings
from app.rooms.actions import (
    dispatch_event,
    handle_disconnect,
)
from app.rooms.protocol import (
    JOIN_EVENT_TYPE,
    make_error_event,
    parse_client_event,
    send_ws_message,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.core.types import LanguageCode
    from app.rooms.manager import GameRoom
    from app.users.models import User

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

    def __init__(self, room: GameRoom, websocket: WebSocket, *, current_user: User | None = None) -> None:
        self.room = room
        self.websocket = websocket
        self.player_id: str | None = None
        self.current_user = current_user
        self._draw_window_start: float = 0.0
        self._draw_count: int = 0

    def resolve_join_locale(self, preferred_locale: LanguageCode | None) -> LanguageCode:
        """Choose the effective locale for this websocket player."""
        if preferred_locale:
            return preferred_locale
        if self.current_user is not None:
            return self.current_user.preferred_locale
        return self.room.metadata.default_locale

    async def run(self) -> None:
        """Send the initial snapshot, then process messages until disconnect."""
        await send_ws_message(self.websocket, self.room.room_state_event())

        while True:
            payload = await self.websocket.receive_text()
            # Reject oversized frames before any JSON parsing/validation work.
            if len(payload) > settings.ws_max_message_bytes:
                await self.send_error("protocol_error", "payload_too_large", "Message too large.")
                continue
            await self.handle(payload)

    def _draw_allowed(self) -> bool:
        """Return whether another draw event fits the per-connection rate window."""
        now = time.monotonic()
        if now - self._draw_window_start >= settings.ws_draw_window_seconds:
            self._draw_window_start = now
            self._draw_count = 0
        self._draw_count += 1
        return self._draw_count <= settings.ws_draw_messages_per_window

    async def handle(self, payload: object) -> None:
        """Parse one inbound message and dispatch it."""
        try:
            event = parse_client_event(payload)
            # Throttle only high-frequency draw events; silently drop the excess
            # so a legitimate fast drawer is never disconnected.
            if event.type in {"draw_stroke", "draw_stroke_partial"} and not self._draw_allowed():
                return
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
            make_error_event(event_type, error=error, message=message),
        )
