"""WebSocket message handler for game rooms."""

import json
import logging
from typing import TYPE_CHECKING

from app.ws_protocol import ValidationError, parse_client_event

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSMessageHandler:
    """Handles incoming WebSocket messages for a game room.

    Each message type has a dedicated ``_handle_*`` method.
    Unknown types fall through to a default broadcast.
    """

    def __init__(self, room, websocket: WebSocket) -> None:
        self.room = room
        self.websocket = websocket
        self._player_id: str | None = None  # Set on successful join; avoids O(n) scan per message

    def _is_host(self, sender_id: str | None) -> bool:
        """Return True if sender_id is the current room host."""
        return self.room.is_host(sender_id)

    async def _send_error(self, event_type: str, error: str, message: str) -> None:
        await self.websocket.send_text(
            json.dumps({"type": event_type, "error": error, "message": message}),
        )

    async def _reject_if_not_host(self, sender_id: str | None, action: str) -> bool:
        if self._is_host(sender_id):
            return False
        logger.info("[Server] Ignored %s from non-host connection", action)
        await self._send_error("permission_error", "host_only", f"Only the host can {action}.")
        return True

    async def handle(self, data: str) -> dict | None:
        """Parse and dispatch a raw WebSocket message string."""
        try:
            event = parse_client_event(data)
            msg_type = event.type

            sender_id = self._player_id

            if msg_type != "join" and sender_id:
                self.room.update_player_activity(sender_id)

            handler = getattr(self, f"_handle_{msg_type}", None) if msg_type else None
            if handler:
                return await handler(event, sender_id)

            # Default: relay to all clients including sender
            payload = event.to_payload()
            await self.room.broadcast(payload)
            return payload

        except (ValueError, ValidationError) as exc:
            logger.info("[Server] Rejected malformed websocket payload: %s", exc)
            await self._send_error("protocol_error", "invalid_payload", "Invalid websocket payload.")
            return None

        except Exception:
            logger.exception("[Server] Error processing message")
            return None

    # ------------------------------------------------------------------
    # Per-type handlers
    # ------------------------------------------------------------------

    async def _handle_join(self, event, sender_id: str | None) -> dict | None:
        player_id = event.player_id
        name = event.name
        try:
            _player, is_reconnecting_host = await self.room.add_player(player_id, name, self.websocket)
            self._player_id = player_id  # Cache for all future messages on this connection
            all_players = self.room.get_player_list()
            logger.info("[Server] Broadcasting player_joined with players: %s", all_players)
            await self.room.broadcast(
                {
                    "type": "player_joined",
                    "playerId": player_id,
                    "name": name,
                    "players": all_players,
                    "isHost": player_id == self.room.host_id,
                },
            )
            if is_reconnecting_host:
                await self.websocket.send_text(
                    json.dumps({"type": "host_restored", "message": "You are still the host"}),
                )
            await self.room.persist()
            return event.to_payload()
        except ValueError as e:
            logger.warning("[Server] Player %s (%s) cannot join: %s", name, player_id, e)
            await self.websocket.send_text(
                json.dumps({"type": "join_error", "error": "room_full", "message": str(e)}),
            )
            await self.websocket.close(code=1008, reason=str(e))
            return None

    async def _handle_start_game(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "start the game"):
            return None
        logger.info("[Server] Raw start_game message: %s", event.to_payload())
        player_count = len(self.room.players)
        if player_count < 2:
            logger.warning(
                "[Server] Cannot start game: Not enough players. Current player count: %s",
                player_count,
            )
            return None
        if self.room.metadata.game_phase != "lobby":
            logger.info("[Server] Ignoring start_game message - game already started.")
            return None
        self.room.configure_game(
            round_length=event.round_length,
            difficulty=event.difficulty,
            max_rounds=event.rounds,
        )
        logger.info("[Server] Game configured with round length: %s seconds", event.round_length)
        payload = event.to_payload()
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_start_round(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "start a round"):
            return None
        round_start_time = self.room.start_round(
            round_number=event.round,
            cards={player_id: card.model_dump(by_alias=True, exclude_none=True) for player_id, card in event.cards.items()},
        )
        logger.info("[Server] Starting round %s at %s", self.room.metadata.current_round, round_start_time)
        payload = {**event.to_payload(), "roundStartTime": round_start_time}
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_round_complete(self, event, sender_id: str | None) -> dict | None:
        logger.info("[Server] Ignoring client-sent round_complete — server handles scoring")
        return event.to_payload()

    async def _handle_game_complete(self, event, sender_id: str | None) -> dict | None:
        logger.info("[Server] Ignoring client-sent game_complete — server handles end-game")
        return event.to_payload()

    async def _handle_player_ready(self, event, sender_id: str | None) -> dict | None:
        player_id = event.player_id
        if not player_id or player_id != sender_id:
            await self._send_error("player_ready_error", "invalid_player", "Ready updates must match your connection.")
            return None
        ready_status = self.room.mark_player_ready(player_id)
        logger.info(
            "[Server] Player %s is ready. Ready count: %s/%s",
            player_id,
            len(self.room.metadata.ready_players),
            len(self.room.players),
        )
        await self.room.broadcast(ready_status)
        await self.room.persist()
        return event.to_payload()

    async def _handle_start_guessing(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "start guessing"):
            return None
        guessing_timeout = self.room.start_guessing()
        self.room.start_scoring_timeout(guessing_timeout)
        payload = event.to_payload()
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_submit_guess(self, event, sender_id: str | None) -> dict | None:
        player_id = event.player_id
        target_player_id = event.target_player_id
        guesses = event.guesses
        if not player_id or player_id != sender_id:
            await self._send_error(
                "submit_guess_error",
                "invalid_player",
                "Guess submissions must match your connection.",
            )
            return None
        if target_player_id:
            await self.room.record_guess_submission(
                player_id=player_id,
                target_player_id=target_player_id,
                guesses=guesses,
            )
        return event.to_payload()

    async def _handle_restart_game(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "restart the game"):
            return None
        logger.info("[Server] Host initiated game restart")
        self.room.reset_game()
        payload = event.to_payload()
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_heartbeat(self, event, sender_id: str | None) -> dict | None:
        # Activity already updated above; no broadcast needed
        return event.to_payload()

    async def _handle_settings_update(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "update room settings"):
            return None
        self.room.metadata.difficulty = event.difficulty or self.room.metadata.difficulty
        self.room.metadata.max_rounds = event.rounds or self.room.metadata.max_rounds
        self.room.metadata.round_length = event.round_length or self.room.metadata.round_length
        payload = event.to_payload()
        logger.info("[Server] Broadcasting settings update from host: %s", payload)
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_language_update(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "update room language"):
            return None
        new_language = event.language
        self.room.metadata.language = new_language
        logger.info("[Server] Host updated room language to %s", new_language)
        await self.room.broadcast({"type": "language_update", "language": new_language})
        await self.room.persist()
        return event.to_payload()

    async def _handle_draw_stroke(self, event, sender_id: str | None) -> dict | None:
        payload = event.to_payload()
        await self.room.broadcast(payload)
        return payload

    # draw_stroke_partial uses the same handler
    _handle_draw_stroke_partial = _handle_draw_stroke

    async def _handle_drawpad_clear(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "clear the drawpad"):
            return None
        logger.info("[Server] Host cleared drawpad")
        payload = event.to_payload()
        await self.room.broadcast(payload)
        return payload

    async def _handle_pad_visibility(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "change pad visibility"):
            return None
        self.room.metadata.pad_visibility = event.visible
        payload = event.to_payload()
        logger.info("[Server] Host updated pad visibility to %s", event.visible)
        await self.room.broadcast(payload)
        await self.room.persist()
        return payload

    async def _handle_privacy_changed(self, event, sender_id: str | None) -> dict | None:
        if await self._reject_if_not_host(sender_id, "change room privacy"):
            return None
        self.room.metadata.is_private = event.is_private
        logger.info("[Server] Host updated room privacy to %s", event.is_private)
        # Privacy is backend-only; no broadcast
        await self.room.persist()
        return event.to_payload()

    async def _handle_initiate_kick(self, event, sender_id: str | None) -> dict | None:
        if sender_id:
            result = await self.room.initiate_kick_vote(sender_id, event.target_player_id)
            if not result.get("success"):
                await self.websocket.send_text(
                    json.dumps(
                        {
                            "type": "kick_error",
                            "error": result.get("error", "Failed to initiate kick vote"),
                        },
                    ),
                )
        return event.to_payload()

    async def _handle_cast_kick_vote(self, event, sender_id: str | None) -> dict | None:
        if sender_id:
            result = await self.room.cast_kick_vote(sender_id, event.target_player_id)
            if not result.get("success"):
                await self.websocket.send_text(
                    json.dumps(
                        {
                            "type": "kick_error",
                            "error": result.get("error", "Failed to cast vote"),
                        },
                    ),
                )
        return event.to_payload()

    async def _handle_request_game_state(self, event, sender_id: str | None) -> dict | None:
        await self.websocket.send_text(json.dumps(self.room.room_state_payload()))
        return event.to_payload()
