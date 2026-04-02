"""WebSocket session handling for game rooms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from app.services.websocket_action_service import (
    handle_cast_kick_vote,
    handle_drawpad_clear,
    handle_initiate_kick,
    handle_join,
    handle_language_update,
    handle_pad_visibility,
    handle_player_ready,
    handle_privacy_changed,
    handle_request_game_state,
    handle_restart_game,
    handle_settings_update,
    handle_start_game,
    handle_start_guessing,
    handle_start_round,
    handle_submit_guess,
)
from app.ws_protocol import (
    JOIN_EVENT_TYPE,
    PlayerLeftEvent,
    ProtocolErrorEvent,
    parse_client_event,
    send_ws_message,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.game_room import GameRoom
    from app.ws_protocol import (
        CastKickVoteEvent,
        DrawpadClearEvent,
        DrawStrokeEvent,
        GameCompleteEvent,
        HeartbeatEvent,
        InitiateKickEvent,
        JoinEvent,
        LanguageUpdateEvent,
        PadVisibilityEvent,
        PlayerReadyEvent,
        PrivacyChangedEvent,
        RequestGameStateEvent,
        RestartGameEvent,
        RoundCompleteEvent,
        SettingsUpdateEvent,
        StartGameEvent,
        StartGuessingEvent,
        StartRoundEvent,
        SubmitGuessEvent,
    )

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

            handler = getattr(self, f"_on_{event.type}", None)
            if handler is None:
                return
            await handler(event)
        except (ValidationError, TypeError, ValueError) as exc:
            logger.info("[Server] Rejected malformed websocket payload: %s", exc)
            await self.send_error("protocol_error", "invalid_payload", "Invalid websocket payload.")
        except Exception:
            logger.exception("[Server] Error processing websocket message")

    async def on_disconnect(self) -> None:
        """Remove the session player from the room and broadcast departure."""
        if not self.player_id:
            return
        await self.room.remove_player(self.player_id)
        await self.room.broadcast(PlayerLeftEvent(playerId=self.player_id))
        await self.room.persist()

    def is_host(self) -> bool:
        """Return whether this connection currently belongs to the host."""
        return self.room.is_host(self.player_id)

    async def send_error(self, event_type: ErrorEventType, error: str, message: str) -> None:
        """Send a recoverable protocol error without closing the connection."""
        await send_ws_message(
            self.websocket,
            ProtocolErrorEvent(type=event_type, error=error, message=message),
        )

    async def _on_join(self, event: JoinEvent) -> None:
        await handle_join(self, event)

    async def _on_start_game(self, event: StartGameEvent) -> None:
        await handle_start_game(self, event)

    async def _on_start_round(self, event: StartRoundEvent) -> None:
        await handle_start_round(self, event)

    async def _on_round_complete(self, event: RoundCompleteEvent) -> None:
        del event

    async def _on_game_complete(self, event: GameCompleteEvent) -> None:
        del event

    async def _on_player_ready(self, event: PlayerReadyEvent) -> None:
        await handle_player_ready(self, event)

    async def _on_start_guessing(self, event: StartGuessingEvent) -> None:
        await handle_start_guessing(self, event)

    async def _on_submit_guess(self, event: SubmitGuessEvent) -> None:
        await handle_submit_guess(self, event)

    async def _on_restart_game(self, event: RestartGameEvent) -> None:
        await handle_restart_game(self, event)

    async def _on_heartbeat(self, event: HeartbeatEvent) -> None:
        del event

    async def _on_settings_update(self, event: SettingsUpdateEvent) -> None:
        await handle_settings_update(self, event)

    async def _on_language_update(self, event: LanguageUpdateEvent) -> None:
        await handle_language_update(self, event)

    async def _on_draw_stroke(self, event: DrawStrokeEvent) -> None:
        await self.room.broadcast(event)

    _on_draw_stroke_partial = _on_draw_stroke

    async def _on_drawpad_clear(self, event: DrawpadClearEvent) -> None:
        await handle_drawpad_clear(self, event)

    async def _on_pad_visibility(self, event: PadVisibilityEvent) -> None:
        await handle_pad_visibility(self, event)

    async def _on_privacy_changed(self, event: PrivacyChangedEvent) -> None:
        await handle_privacy_changed(self, event)

    async def _on_initiate_kick(self, event: InitiateKickEvent) -> None:
        await handle_initiate_kick(self, event)

    async def _on_cast_kick_vote(self, event: CastKickVoteEvent) -> None:
        await handle_cast_kick_vote(self, event)

    async def _on_request_game_state(self, event: RequestGameStateEvent) -> None:
        await handle_request_game_state(self, event)
