"""WebSocket message handler for game rooms."""

import json
import logging
import time

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
        return bool(sender_id and self.room.host_id and sender_id == self.room.host_id)

    async def handle(self, data: str) -> dict | None:
        """Parse and dispatch a raw WebSocket message string."""
        try:
            message = json.loads(data)
            msg_type = message.get("type")

            sender_id = self._player_id

            if msg_type != "join" and sender_id:
                self.room.update_player_activity(sender_id)

            handler = getattr(self, f"_handle_{msg_type}", None) if msg_type else None
            if handler:
                return await handler(message, sender_id)

            # Default: relay to all clients including sender
            await self.room.broadcast(message)
            return message

        except Exception:
            logger.exception("[Server] Error processing message")
            return None

    # ------------------------------------------------------------------
    # Per-type handlers
    # ------------------------------------------------------------------

    async def _handle_join(self, message: dict, sender_id: str | None) -> dict | None:
        player_id = message.get("playerId")
        name = message.get("name")
        try:
            player, is_reconnecting_host = await self.room.add_player(player_id, name, self.websocket)
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
            return message
        except ValueError as e:
            logger.warning("[Server] Player %s (%s) cannot join: %s", name, player_id, e)
            await self.websocket.send_text(
                json.dumps({"type": "join_error", "error": "room_full", "message": str(e)}),
            )
            await self.websocket.close(code=1008, reason=str(e))
            return None

    async def _handle_start_game(self, message: dict, sender_id: str | None) -> dict | None:
        logger.info("[Server] Raw start_game message: %s", json.dumps(message))
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
        self.room.metadata.round_length = message.get("roundLength")
        self.room.metadata.difficulty = message.get("difficulty")
        self.room.metadata.max_rounds = message.get("rounds") or 5
        self.room.metadata.game_phase = "drawing"
        self.room.metadata.current_round = 0
        self.room.metadata.player_scores = dict.fromkeys(self.room.players, 0)
        self.room.metadata.ready_players.clear()
        logger.info("[Server] Game configured with round length: %s seconds", message.get("roundLength"))
        await self.room.broadcast(message)
        await self.room.persist()
        return message

    async def _handle_start_round(self, message: dict, sender_id: str | None) -> dict | None:
        round_start_time = int(time.time() * 1000)
        self.room.metadata.round_start_time = round_start_time
        self.room.metadata.game_phase = "drawing"
        self.room.metadata.current_round = message.get("round", self.room.metadata.current_round + 1)
        self.room.metadata.player_cards = message.get("cards", {})
        self.room.metadata.guess_submissions = []
        self.room.metadata.submitted_players = set()
        self.room.metadata.player_count_for_scoring = len(self.room.players)
        for pid in self.room.players:
            if pid not in self.room.metadata.player_scores:
                self.room.metadata.player_scores[pid] = 0
        if self.room._round_scoring_task:
            self.room._round_scoring_task.cancel()
            self.room._round_scoring_task = None
        self.room.metadata.ready_players.clear()
        logger.info("[Server] Starting round %s at %s", self.room.metadata.current_round, round_start_time)
        await self.room.broadcast({**message, "roundStartTime": round_start_time})
        await self.room.persist()
        return message

    async def _handle_round_complete(self, message: dict, sender_id: str | None) -> dict | None:
        logger.info("[Server] Ignoring client-sent round_complete — server handles scoring")
        return message

    async def _handle_game_complete(self, message: dict, sender_id: str | None) -> dict | None:
        logger.info("[Server] Ignoring client-sent game_complete — server handles end-game")
        return message

    async def _handle_player_ready(self, message: dict, sender_id: str | None) -> dict | None:
        player_id = message.get("playerId")
        self.room.metadata.ready_players.add(player_id)
        logger.info(
            "[Server] Player %s is ready. Ready count: %s/%s",
            player_id,
            len(self.room.metadata.ready_players),
            len(self.room.players),
        )
        await self.room.broadcast(
            {
                "type": "ready_status",
                "readyCount": len(self.room.metadata.ready_players),
                "totalPlayers": len(self.room.players),
            },
        )
        await self.room.persist()
        return message

    async def _handle_start_guessing(self, message: dict, sender_id: str | None) -> dict | None:
        self.room.metadata.game_phase = "guessing"
        self.room.metadata.player_count_for_scoring = len(self.room.players)
        guessing_timeout = self.room.metadata.round_length or 30
        self.room.start_scoring_timeout(guessing_timeout)
        await self.room.broadcast(message)
        await self.room.persist()
        return message

    async def _handle_submit_guess(self, message: dict, sender_id: str | None) -> dict | None:
        player_id = message.get("playerId")
        target_player_id = message.get("targetPlayerId")
        guesses = message.get("guesses", [])
        if player_id and target_player_id:
            self.room.metadata.guess_submissions.append(
                {"playerId": player_id, "targetPlayerId": target_player_id, "guesses": guesses},
            )
            self.room.metadata.submitted_players.add(player_id)
            submitted = len(self.room.metadata.submitted_players)
            expected = self.room.metadata.player_count_for_scoring
            logger.info(
                "[Server] Guess submitted by %s: %s/%s players submitted",
                player_id,
                submitted,
                expected,
            )
            if expected > 0 and submitted >= expected:
                await self.room.score_and_broadcast_round()
        return message

    async def _handle_restart_game(self, message: dict, sender_id: str | None) -> dict | None:
        logger.info("[Server] Host initiated game restart")
        if self.room._round_scoring_task:
            self.room._round_scoring_task.cancel()
            self.room._round_scoring_task = None
        self.room.metadata.player_scores = {}
        self.room.metadata.current_round = 0
        self.room.metadata.guess_submissions = []
        self.room.metadata.submitted_players = set()
        self.room.metadata.player_cards = {}
        self.room.metadata.ready_players.clear()
        self.room.metadata.game_phase = "lobby"
        await self.room.broadcast(message)
        await self.room.persist()
        return message

    async def _handle_heartbeat(self, message: dict, sender_id: str | None) -> dict | None:
        # Activity already updated above; no broadcast needed
        return message

    async def _handle_settings_update(self, message: dict, sender_id: str | None) -> dict | None:
        if self._is_host(sender_id):
            self.room.metadata.difficulty = message.get("difficulty", self.room.metadata.difficulty)
            self.room.metadata.max_rounds = message.get("rounds", self.room.metadata.max_rounds)
            self.room.metadata.round_length = message.get("roundLength", self.room.metadata.round_length)
            logger.info("[Server] Broadcasting settings update from host: %s", message)
            await self.room.broadcast(message)
            await self.room.persist()
        else:
            logger.info("[Server] Ignored settings_update from non-host connection")
        return message

    async def _handle_language_update(self, message: dict, sender_id: str | None) -> dict | None:
        if self._is_host(sender_id):
            new_language = message.get("language", "en")
            self.room.metadata.language = new_language
            logger.info("[Server] Host updated room language to %s", new_language)
            await self.room.broadcast({"type": "language_update", "language": new_language})
            await self.room.persist()
        else:
            logger.info("[Server] Ignored language_update from non-host connection")
        return message

    async def _handle_draw_stroke(self, message: dict, sender_id: str | None) -> dict | None:
        await self.room.broadcast(message)
        return message

    # draw_stroke_partial uses the same handler
    _handle_draw_stroke_partial = _handle_draw_stroke

    async def _handle_drawpad_clear(self, message: dict, sender_id: str | None) -> dict | None:
        if self._is_host(sender_id):
            logger.info("[Server] Host cleared drawpad")
            await self.room.broadcast(message)
        else:
            logger.info("[Server] Ignored drawpad_clear from non-host connection")
        return message

    async def _handle_pad_visibility(self, message: dict, sender_id: str | None) -> dict | None:
        if self._is_host(sender_id):
            self.room.metadata.pad_visibility = message.get("visible", True)
            logger.info("[Server] Host updated pad visibility to %s", message.get("visible"))
            await self.room.broadcast(message)
            await self.room.persist()
        else:
            logger.info("[Server] Ignored pad_visibility from non-host connection")
        return message

    async def _handle_privacy_changed(self, message: dict, sender_id: str | None) -> dict | None:
        if self._is_host(sender_id):
            self.room.metadata.is_private = message.get("isPrivate", False)
            logger.info("[Server] Host updated room privacy to %s", message.get("isPrivate"))
            # Privacy is backend-only; no broadcast
            await self.room.persist()
        else:
            logger.info("[Server] Ignored privacy_changed from non-host connection")
        return message

    async def _handle_initiate_kick(self, message: dict, sender_id: str | None) -> dict | None:
        if sender_id:
            target_player_id = message.get("targetPlayerId")
            if target_player_id:
                result = await self.room.initiate_kick_vote(sender_id, target_player_id)
                if not result.get("success"):
                    await self.websocket.send_text(
                        json.dumps(
                            {
                                "type": "kick_error",
                                "error": result.get("error", "Failed to initiate kick vote"),
                            },
                        ),
                    )
            else:
                logger.warning("[Server] Missing targetPlayerId in initiate_kick message")
        return message

    async def _handle_cast_kick_vote(self, message: dict, sender_id: str | None) -> dict | None:
        if sender_id:
            target_player_id = message.get("targetPlayerId")
            if target_player_id:
                result = await self.room.cast_kick_vote(sender_id, target_player_id)
                if not result.get("success"):
                    await self.websocket.send_text(
                        json.dumps(
                            {
                                "type": "kick_error",
                                "error": result.get("error", "Failed to cast vote"),
                            },
                        ),
                    )
            else:
                logger.warning("[Server] Missing targetPlayerId in cast_kick_vote message")
        return message

    async def _handle_request_game_state(self, message: dict, sender_id: str | None) -> dict | None:
        players_with_categories = [
            {"id": p.id, "name": p.name, "categories": p.categories} for p in self.room.players.values()
        ]
        await self.websocket.send_text(
            json.dumps(
                {
                    "type": "room_state",
                    "players": players_with_categories,
                    "hostId": self.room.host_id,
                    "categories": self.room.metadata.categories,
                    "gamePhase": self.room.metadata.game_phase,
                    "roundStartTime": self.room.metadata.round_start_time,
                    "roundLength": self.room.metadata.round_length,
                    "language": self.room.metadata.language,
                },
            ),
        )
        return message
