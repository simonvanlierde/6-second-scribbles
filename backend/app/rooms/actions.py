"""Action handlers for room websocket sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.types import GamePhase
from app.rooms import rounds
from app.rooms.player_lifecycle import IDENTITY_CONFLICT_ERROR, KICKED_ERROR
from app.rooms.protocol import (
    DefaultLocaleUpdateServerEvent,
    DrawStrokePartialEvent,
    HostRestoredEvent,
    JoinErrorEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
    ReactionReceivedServerEvent,
    send_ws_message,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.rooms.manager import GameRoom
    from app.rooms.protocol import (
        CastKickVoteEvent,
        ClientEventModel,
        DefaultLocaleUpdateEvent,
        DrawpadClearEvent,
        DrawStrokeEvent,
        GameSettingsEventModel,
        InitiateKickEvent,
        JoinEvent,
        LeaveEvent,
        PadVisibilityEvent,
        PlayerReadyEvent,
        PrivacyChangedEvent,
        ReactionSendEvent,
        RequestGameStateEvent,
        RestartGameEvent,
        SettingsUpdateEvent,
        StartGameEvent,
        SubmitGuessEvent,
        WatchEvent,
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


def _with_stored_settings[T: GameSettingsEventModel](event: T, room: GameRoom) -> T:
    """Return a copy of a settings event that carries the room's stored settings."""
    metadata = room.metadata
    return event.model_copy(
        update={
            "difficulty": metadata.difficulty,
            "rounds": metadata.max_rounds,
            "drawing_time_limit": metadata.drawing_time_limit,
            "guessing_time_limit": metadata.guessing_time_limit,
        },
    )


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
            rejoin_key=event.rejoin_key,
        )
    except ValueError as exc:
        logger.warning("[Server] Player %s (%s) cannot join: %s", event.name, event.player_id, exc)
        if str(exc) == IDENTITY_CONFLICT_ERROR:
            error, message = IDENTITY_CONFLICT_ERROR, "This player is already in use in another browser or account."
        elif str(exc) == KICKED_ERROR:
            error, message = KICKED_ERROR, "You were removed from this room."
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
    await broadcast_and_persist(session, _with_stored_settings(event, session.room))
    session.room.scheduler.schedule_first_round()


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
    await broadcast_and_persist(session, _with_stored_settings(event, room))


async def handle_default_locale_update(session: RoomWebSocketSession, event: DefaultLocaleUpdateEvent) -> None:
    """Handle a default-locale update event."""
    if not await require_host(session, "update the room default locale"):
        return
    session.room.metadata.default_locale = event.locale
    await broadcast_and_persist(session, DefaultLocaleUpdateServerEvent(locale=event.locale))


async def handle_drawpad_clear(session: RoomWebSocketSession, event: DrawpadClearEvent) -> None:
    """Handle a drawpad-clear event."""
    if not await require_host(session, "clear the drawpad"):
        return
    session.room.clear_lobby_strokes()
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
    if error := await session.room.initiate_kick_vote(session.player_id, event.target_player_id):
        await session.send_error("kick_error", error, "")


async def handle_cast_kick_vote(session: RoomWebSocketSession, event: CastKickVoteEvent) -> None:
    """Handle casting a kick vote."""
    if not session.player_id:
        return
    if error := await session.room.cast_kick_vote(session.player_id, event.target_player_id):
        await session.send_error("kick_error", error, "")


async def handle_request_game_state(session: RoomWebSocketSession, event: RequestGameStateEvent) -> None:
    """Handle a request-game-state event."""
    del event
    if not session.state_request_allowed():
        return
    await send_ws_message(session.websocket, session.room.room_state_event(for_player_id=session.player_id))


async def handle_watch(session: RoomWebSocketSession, event: WatchEvent) -> None:
    """Register the connection as a spectator, then send it a fresh snapshot."""
    del event
    if session.player_id or session.is_observer:
        return
    if not session.room.add_observer(session.websocket):
        message = "This room has as many spectators as it allows."
        await send_ws_message(session.websocket, JoinErrorEvent(error="spectators_full", message=message))
        await session.websocket.close(code=1008, reason=message)
        return
    session.is_observer = True
    # The connect-time snapshot may predate broadcasts this socket missed before now.
    await send_ws_message(session.websocket, session.room.room_state_event())


async def handle_draw_stroke(session: RoomWebSocketSession, event: DrawStrokeEvent | DrawStrokePartialEvent) -> None:
    """Handle a draw-stroke event (broadcast as-is).

    The in-game path carries a full `drawing` PNG; retain the latest one per player
    so reconnecting clients recover it via room_state. The lobby shared drawpad
    relays vector `stroke` fragments; fold those into the room's authoritative
    stroke list so late joiners hydrate the collective doodle via room_state.
    """
    if not session.player_id:
        return
    # Clients pick the drawing to show from the relayed playerId, so it must be
    # the sender's own: a forged id would overwrite another player's drawing.
    event.player_id = session.player_id
    if isinstance(event, DrawStrokePartialEvent):
        # Only the lobby's shared drawpad sends fragments.
        if session.room.metadata.game_phase != GamePhase.LOBBY:
            return
        if event.stroke is not None:
            session.room.apply_lobby_partial(session.player_id, event.stroke, is_start=event.stroke_start)
    else:
        drawing = (event.model_extra or {}).get("drawing")
        if isinstance(drawing, str):
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
    if session.is_observer:
        session.room.remove_observer(session.websocket)
        return
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
    await session.room.remove_player(session.player_id, forget_identity=True)
    await broadcast_and_persist(session, PlayerLeftEvent(playerId=session.player_id))


# Dispatch table mapping event type strings to their handler functions.
# Events not listed here (round_complete, game_complete, heartbeat) are
# server-originated echoes that require no server-side action.
_HANDLERS: dict[str, _Handler] = {
    "join": handle_join,
    "leave": handle_leave,
    "start_game": handle_start_game,
    "player_ready": handle_player_ready,
    "submit_guess": handle_submit_guess,
    "restart_game": handle_restart_game,
    "settings_update": handle_settings_update,
    "default_locale_update": handle_default_locale_update,
    "draw_stroke": handle_draw_stroke,
    "draw_stroke_partial": handle_draw_stroke,
    "drawpad_clear": handle_drawpad_clear,
    "pad_visibility": handle_pad_visibility,
    "privacy_changed": handle_privacy_changed,
    "initiate_kick": handle_initiate_kick,
    "cast_kick_vote": handle_cast_kick_vote,
    "request_game_state": handle_request_game_state,
    "watch": handle_watch,
    "reaction_send": handle_reaction_send,
}


async def dispatch_event(session: RoomWebSocketSession, event: ClientEventModel) -> None:
    """Dispatch a parsed client event to its handler."""
    handler = _HANDLERS.get(event.type)
    if handler:
        await handler(session, event)
