"""Action handlers for room websocket sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.types import LOBBY_PHASE
from app.rooms import mutations
from app.rooms.protocol import (
    HostRestoredEvent,
    JoinErrorEvent,
    LanguageUpdatedEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
    PlayerListItem,
    StartRoundBroadcastEvent,
    send_ws_message,
)
from app.rooms.state import PlayerCardState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.rooms.protocol import (
        CastKickVoteEvent,
        ClientEventModel,
        DrawpadClearEvent,
        DrawStrokeEvent,
        DrawStrokePartialEvent,
        InitiateKickEvent,
        JoinEvent,
        LanguageUpdateEvent,
        PadVisibilityEvent,
        PlayerReadyEvent,
        PrivacyChangedEvent,
        RequestGameStateEvent,
        RestartGameEvent,
        SettingsUpdateEvent,
        StartGameEvent,
        StartGuessingEvent,
        StartRoundEvent,
        SubmitGuessEvent,
        WebSocketMessage,
    )
    from app.rooms.session import RoomWebSocketSession

logger = logging.getLogger(__name__)

type _Handler = Callable[[RoomWebSocketSession, Any], Awaitable[None]]


async def require_host(session: RoomWebSocketSession, action: str) -> bool:
    """Return whether a host-only action may continue."""
    if session.is_host():
        return True
    logger.info("[Server] Ignored %s from non-host connection", action)
    await session.send_error("permission_error", "host_only", f"Only the host can {action}.")
    return False


async def broadcast_and_persist(session: RoomWebSocketSession, event: WebSocketMessage) -> None:
    """Broadcast an event to the room and persist the updated state."""
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_join(session: RoomWebSocketSession, event: JoinEvent) -> None:
    """Handle a join event for one websocket session."""
    try:
        _player, is_reconnecting_host = await session.room.add_player(event.player_id, event.name, session.websocket)
    except ValueError as exc:
        logger.warning("[Server] Player %s (%s) cannot join: %s", event.name, event.player_id, exc)
        await send_ws_message(
            session.websocket,
            JoinErrorEvent(error="room_full", message=str(exc)),
        )
        await session.websocket.close(code=1008, reason=str(exc))
        return

    session.player_id = event.player_id
    await session.room.broadcast(
        PlayerJoinedEvent(
            playerId=event.player_id,
            name=event.name,
            players=[PlayerListItem(**player) for player in session.room.get_player_list()],
            isHost=event.player_id == session.room.host_id,
        ),
    )
    if is_reconnecting_host:
        await send_ws_message(session.websocket, HostRestoredEvent(message="You are still the host"))
    await session.room.persist()


async def handle_start_game(session: RoomWebSocketSession, event: StartGameEvent) -> None:
    """Handle a start-game event."""
    if not await require_host(session, "start the game"):
        return
    if len(session.room.players) < 2 or session.room.metadata.game_phase != LOBBY_PHASE:
        return
    session.room.configure_game(
        round_length=event.round_length,
        difficulty=event.difficulty,
        max_rounds=event.rounds,
    )
    await broadcast_and_persist(session, event)
    session.room.start_first_round_timeout()


async def handle_start_round(session: RoomWebSocketSession, event: StartRoundEvent) -> None:
    """Handle a start-round event."""
    if not await require_host(session, "start a round"):
        return
    round_start_time = session.room.start_round(
        round_number=event.round,
        cards={
            player_id: PlayerCardState.model_validate(card.model_dump(exclude_none=True))
            for player_id, card in event.cards.items()
        },
    )
    await broadcast_and_persist(
        session,
        StartRoundBroadcastEvent(
            type="start_round",
            round=event.round,
            cards=event.cards,
            roundStartTime=round_start_time,
        ),
    )
    session.room.start_guessing_timeout(session.room.metadata.round_length or 30)


async def handle_player_ready(session: RoomWebSocketSession, event: PlayerReadyEvent) -> None:
    """Handle a player-ready event."""
    if event.player_id != session.player_id:
        await session.send_error("player_ready_error", "invalid_player", "Ready updates must match your connection.")
        return
    await broadcast_and_persist(session, session.room.mark_player_ready(event.player_id))


async def handle_start_guessing(session: RoomWebSocketSession, event: StartGuessingEvent) -> None:
    """Handle a start-guessing event."""
    if not await require_host(session, "start guessing"):
        return
    session.room.start_scoring_timeout(session.room.start_guessing())
    await broadcast_and_persist(session, event)


async def handle_submit_guess(session: RoomWebSocketSession, event: SubmitGuessEvent) -> None:
    """Handle a submit-guess event."""
    if event.player_id != session.player_id:
        await session.send_error(
            "submit_guess_error",
            "invalid_player",
            "Guess submissions must match your connection.",
        )
        return
    await session.room.record_guess_submission(
        player_id=event.player_id,
        target_player_id=event.target_player_id,
        guesses=event.guesses,
    )


async def handle_restart_game(session: RoomWebSocketSession, event: RestartGameEvent) -> None:
    """Handle a restart-game event."""
    if not await require_host(session, "restart the game"):
        return
    session.room.reset_game()
    await broadcast_and_persist(session, event)


async def handle_settings_update(session: RoomWebSocketSession, event: SettingsUpdateEvent) -> None:
    """Handle a settings-update event."""
    if not await require_host(session, "update room settings"):
        return
    mutations.apply_settings_update(
        session.room,
        difficulty=event.difficulty,
        rounds=event.rounds,
        round_length=event.round_length,
    )
    await broadcast_and_persist(session, event)


async def handle_language_update(session: RoomWebSocketSession, event: LanguageUpdateEvent) -> None:
    """Handle a language-update event."""
    if not await require_host(session, "update room language"):
        return
    mutations.set_language(session.room, event.language)
    await broadcast_and_persist(session, LanguageUpdatedEvent(language=event.language))


async def handle_drawpad_clear(session: RoomWebSocketSession, event: DrawpadClearEvent) -> None:
    """Handle a drawpad-clear event."""
    if not await require_host(session, "clear the drawpad"):
        return
    await session.room.broadcast(event)


async def handle_pad_visibility(session: RoomWebSocketSession, event: PadVisibilityEvent) -> None:
    """Handle a pad-visibility event."""
    if not await require_host(session, "change pad visibility"):
        return
    mutations.set_pad_visibility(session.room, visible=event.visible)
    await broadcast_and_persist(session, event)


async def handle_privacy_changed(session: RoomWebSocketSession, event: PrivacyChangedEvent) -> None:
    """Handle a privacy-changed event."""
    if not await require_host(session, "change room privacy"):
        return
    mutations.set_privacy(session.room, is_private=event.is_private)
    await session.room.persist()


async def handle_initiate_kick(session: RoomWebSocketSession, event: InitiateKickEvent) -> None:
    """Handle initiating a kick vote."""
    if not session.player_id:
        return
    result = await session.room.initiate_kick_vote(session.player_id, event.target_player_id)
    if not result.success:
        await session.send_error("kick_error", result.error or "Failed to initiate kick vote", "")


async def handle_cast_kick_vote(session: RoomWebSocketSession, event: CastKickVoteEvent) -> None:
    """Handle casting a kick vote."""
    if not session.player_id:
        return
    result = await session.room.cast_kick_vote(session.player_id, event.target_player_id)
    if not result.success:
        await session.send_error("kick_error", result.error or "Failed to cast vote", "")


async def handle_request_game_state(session: RoomWebSocketSession, event: RequestGameStateEvent) -> None:
    """Handle a request-game-state event."""
    del event
    await send_ws_message(session.websocket, session.room.room_state_event())


async def handle_draw_stroke(session: RoomWebSocketSession, event: DrawStrokeEvent | DrawStrokePartialEvent) -> None:
    """Handle a draw-stroke event (broadcast as-is)."""
    await session.room.broadcast(event)


async def handle_disconnect(session: RoomWebSocketSession) -> None:
    """Remove the session player from the room and broadcast departure."""
    if not session.player_id:
        return
    await session.room.remove_player(session.player_id)
    await broadcast_and_persist(session, PlayerLeftEvent(playerId=session.player_id))


# Dispatch table mapping event type strings to their handler functions.
# Events not listed here (round_complete, game_complete, heartbeat) are
# server-originated echoes that require no server-side action.
_HANDLERS: dict[str, _Handler] = {
    "join": handle_join,
    "start_game": handle_start_game,
    "start_round": handle_start_round,
    "player_ready": handle_player_ready,
    "start_guessing": handle_start_guessing,
    "submit_guess": handle_submit_guess,
    "restart_game": handle_restart_game,
    "settings_update": handle_settings_update,
    "language_update": handle_language_update,
    "draw_stroke": handle_draw_stroke,
    "draw_stroke_partial": handle_draw_stroke,
    "drawpad_clear": handle_drawpad_clear,
    "pad_visibility": handle_pad_visibility,
    "privacy_changed": handle_privacy_changed,
    "initiate_kick": handle_initiate_kick,
    "cast_kick_vote": handle_cast_kick_vote,
    "request_game_state": handle_request_game_state,
}


async def dispatch_event(session: RoomWebSocketSession, event: ClientEventModel) -> None:
    """Dispatch a parsed client event to its handler."""
    handler = _HANDLERS.get(event.type)
    if handler:
        await handler(session, event)
