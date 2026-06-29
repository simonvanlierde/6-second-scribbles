"""Action handlers for room websocket sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.types import GamePhase
from app.rooms import rounds
from app.rooms.player_lifecycle import IDENTITY_CONFLICT_ERROR
from app.rooms.protocol import (
    DefaultLocaleUpdateServerEvent,
    HostRestoredEvent,
    JoinErrorEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
    ReactionReceivedServerEvent,
    RoomCustomCategoriesUpdateServerEvent,
    StartGuessingEvent,
    StartRoundServerEvent,
    send_ws_message,
)
from app.rooms.state import PlayerPromptAssignmentState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.rooms.protocol import (
        CastKickVoteEvent,
        ClientEventModel,
        DefaultLocaleUpdateEvent,
        DrawpadClearEvent,
        DrawStrokeEvent,
        DrawStrokePartialEvent,
        InitiateKickEvent,
        JoinEvent,
        LeaveEvent,
        PadVisibilityEvent,
        PlayerReadyEvent,
        PrivacyChangedEvent,
        ReactionSendEvent,
        RequestGameStateEvent,
        RestartGameEvent,
        RoomCustomCategoriesUpdateEvent,
        SettingsUpdateEvent,
        StartGameEvent,
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
    # Block brand-new players mid-round, but always let an existing participant
    # reconnect (e.g. after a page refresh). A participant is identified by
    # having been dealt a card for the current round.
    is_rejoining_participant = event.player_id in session.room.metadata.player_assignments
    if session.room.metadata.game_phase in (GamePhase.DRAWING, GamePhase.GUESSING) and not is_rejoining_participant:
        await send_ws_message(
            session.websocket,
            JoinErrorEvent(
                error="game_in_progress",
                message="This round is already in progress. You can join for the next round.",
            ),
        )
        return

    try:
        _player, is_reconnecting_host = await session.room.add_player(
            event.player_id,
            event.name,
            session.websocket,
            preferred_locale=session.resolve_join_locale(event.preferred_locale),
            user_id=session.current_user.id if session.current_user is not None else None,
            preferred_color=event.preferred_color,
        )
    except ValueError as exc:
        logger.warning("[Server] Player %s (%s) cannot join: %s", event.name, event.player_id, exc)
        if str(exc) == IDENTITY_CONFLICT_ERROR:
            error, message = IDENTITY_CONFLICT_ERROR, "This player is already in use by another account."
        else:
            error, message = "room_full", str(exc)
        await send_ws_message(
            session.websocket,
            JoinErrorEvent(error=error, message=message),
        )
        await session.websocket.close(code=1008, reason=message)
        return

    session.player_id = event.player_id
    await session.room.broadcast(
        PlayerJoinedEvent(
            playerId=event.player_id,
            name=event.name,
            players=session.room.get_player_list(),
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
    if len(session.room.players) < 2 or session.room.metadata.game_phase != GamePhase.LOBBY:
        return
    if session.room.scheduler.is_next_round_pending():
        return
    rounds.configure_game(
        session.room,
        drawing_time_limit=event.drawing_time_limit,
        guessing_time_limit=event.guessing_time_limit,
        difficulty=event.difficulty,
        max_rounds=event.rounds,
    )
    await broadcast_and_persist(session, event)
    session.room.scheduler.schedule_first_round()


async def handle_start_round(session: RoomWebSocketSession, event: StartRoundEvent) -> None:
    """Handle a start-round event."""
    if not await require_host(session, "start a round"):
        return
    round_start_time = session.room.start_round(
        round_number=event.round,
        cards={
            player_id: PlayerPromptAssignmentState(
                category_id=card.category_id,
                category=card.category,
                item_ids=card.item_ids or [],
                items=card.items,
                alternatives=card.alternatives or {},
            )
            for player_id, card in event.cards.items()
        },
    )
    await broadcast_and_persist(
        session,
        StartRoundServerEvent(
            type="start_round",
            round=event.round,
            cards=event.cards,
            roundStartTime=round_start_time,
        ),
    )
    session.room.scheduler.schedule_guessing_start(session.room.metadata.drawing_time_limit or 30)


async def handle_player_ready(session: RoomWebSocketSession, event: PlayerReadyEvent) -> None:
    """Handle a player-ready event."""
    if event.player_id != session.player_id:
        await session.send_error("player_ready_error", "invalid_player", "Ready updates must match your connection.")
        return
    ready_status = session.room.mark_player_ready(event.player_id)
    await broadcast_and_persist(session, ready_status)

    if session.room.metadata.game_phase == GamePhase.DRAWING and rounds.all_connected_players_ready(session.room):
        session.room.scheduler.schedule_scoring_timeout(session.room.start_guessing())
        await broadcast_and_persist(session, rounds.guessing_event_payload(session.room))


async def handle_start_guessing(session: RoomWebSocketSession, event: StartGuessingEvent) -> None:
    """Handle a start-guessing event."""
    del event
    if not await require_host(session, "start guessing"):
        return
    session.room.scheduler.schedule_scoring_timeout(session.room.start_guessing())
    await broadcast_and_persist(session, rounds.guessing_event_payload(session.room))


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
    # Players who dropped during the finished game and never returned are cleared
    # as we go back to the lobby (they were kept through final results).
    await session.room.prune_disconnected()
    await broadcast_and_persist(session, event)


async def handle_settings_update(session: RoomWebSocketSession, event: SettingsUpdateEvent) -> None:
    """Handle a settings-update event."""
    if not await require_host(session, "update room settings"):
        return
    room = session.room
    room.metadata.difficulty = event.difficulty or room.metadata.difficulty
    room.metadata.max_rounds = event.rounds or room.metadata.max_rounds
    room.metadata.drawing_time_limit = event.drawing_time_limit or room.metadata.drawing_time_limit
    room.metadata.guessing_time_limit = event.guessing_time_limit or room.metadata.guessing_time_limit
    await broadcast_and_persist(session, event)


async def handle_default_locale_update(session: RoomWebSocketSession, event: DefaultLocaleUpdateEvent) -> None:
    """Handle a default-locale update event."""
    if not await require_host(session, "update the room default locale"):
        return
    session.room.metadata.default_locale = event.locale
    await broadcast_and_persist(session, DefaultLocaleUpdateServerEvent(locale=event.locale))


async def handle_room_custom_categories_update(
    session: RoomWebSocketSession,
    event: RoomCustomCategoriesUpdateEvent,
) -> None:
    """Handle a host updating room-level private category overrides."""
    if not await require_host(session, "update room categories"):
        return
    category_ids = event.category_ids
    session.room.metadata.custom_category_ids = sorted(set(category_ids)) if category_ids is not None else None
    await broadcast_and_persist(
        session,
        RoomCustomCategoriesUpdateServerEvent(category_ids=session.room.metadata.custom_category_ids),
    )


async def handle_drawpad_clear(session: RoomWebSocketSession, event: DrawpadClearEvent) -> None:
    """Handle a drawpad-clear event."""
    if not await require_host(session, "clear the drawpad"):
        return
    await session.room.broadcast(event)


async def handle_pad_visibility(session: RoomWebSocketSession, event: PadVisibilityEvent) -> None:
    """Handle a pad-visibility event."""
    if not await require_host(session, "change pad visibility"):
        return
    session.room.metadata.pad_visibility = event.visible
    await broadcast_and_persist(session, event)


async def handle_privacy_changed(session: RoomWebSocketSession, event: PrivacyChangedEvent) -> None:
    """Handle a privacy-changed event."""
    if not await require_host(session, "change room privacy"):
        return
    session.room.metadata.is_private = event.is_private
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
    await send_ws_message(session.websocket, session.room.room_state_event(for_player_id=session.player_id))


async def handle_draw_stroke(session: RoomWebSocketSession, event: DrawStrokeEvent | DrawStrokePartialEvent) -> None:
    """Handle a draw-stroke event (broadcast as-is).

    A completed stroke carries a full `drawing` PNG; retain the latest one per
    player so reconnecting clients can recover it via room_state.
    """
    drawing = (event.model_extra or {}).get("drawing")
    if session.player_id and isinstance(drawing, str):
        session.room.round_drawings[session.player_id] = drawing
    await session.room.broadcast(event)


async def handle_reaction_send(session: RoomWebSocketSession, event: ReactionSendEvent) -> None:
    """Broadcast an ephemeral drawing reaction to everyone in the room (sender included)."""
    if not session.player_id:
        return
    await session.room.broadcast(
        ReactionReceivedServerEvent(
            drawingId=event.drawing_id,
            reactionKey=event.reaction_key,
            senderId=session.player_id,
        ),
    )


async def handle_disconnect(session: RoomWebSocketSession) -> None:
    """Handle a dropped socket.

    Mark the player reconnecting (mid-game) or remove them (lobby); an explicit
    leave goes through handle_leave instead.
    """
    if not session.player_id:
        return
    # On reconnect (e.g. a page refresh) a newer socket may already have re-added
    # this player. If the room's player is now bound to a different websocket,
    # this is the stale connection tearing down — leave the live one intact.
    current = session.room.players.get(session.player_id)
    if current is not None and current.websocket is not session.websocket:
        return
    await session.room.disconnect_player(session.player_id)


async def handle_leave(session: RoomWebSocketSession, event: LeaveEvent) -> None:
    """Handle an explicit, intentional leave — remove the player right away."""
    del event
    if not session.player_id:
        return
    await session.room.remove_player(session.player_id)
    await broadcast_and_persist(session, PlayerLeftEvent(playerId=session.player_id))


# Dispatch table mapping event type strings to their handler functions.
# Events not listed here (round_complete, game_complete, heartbeat) are
# server-originated echoes that require no server-side action.
_HANDLERS: dict[str, _Handler] = {
    "join": handle_join,
    "leave": handle_leave,
    "start_game": handle_start_game,
    "start_round": handle_start_round,
    "player_ready": handle_player_ready,
    "start_guessing": handle_start_guessing,
    "submit_guess": handle_submit_guess,
    "restart_game": handle_restart_game,
    "settings_update": handle_settings_update,
    "default_locale_update": handle_default_locale_update,
    "room_custom_categories_update": handle_room_custom_categories_update,
    "draw_stroke": handle_draw_stroke,
    "draw_stroke_partial": handle_draw_stroke,
    "drawpad_clear": handle_drawpad_clear,
    "pad_visibility": handle_pad_visibility,
    "privacy_changed": handle_privacy_changed,
    "initiate_kick": handle_initiate_kick,
    "cast_kick_vote": handle_cast_kick_vote,
    "request_game_state": handle_request_game_state,
    "reaction_send": handle_reaction_send,
}


async def dispatch_event(session: RoomWebSocketSession, event: ClientEventModel) -> None:
    """Dispatch a parsed client event to its handler."""
    handler = _HANDLERS.get(event.type)
    if handler:
        await handler(session, event)
