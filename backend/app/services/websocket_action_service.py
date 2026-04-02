"""Action handlers for room websocket sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.websocket_session_protocol import WebSocketSessionContext  # noqa: TC001 - used in runtime annotations
from app.ws_protocol import (
    HostRestoredEvent,
    LanguageUpdatedEvent,
    PlayerJoinedEvent,
    PlayerListItem,
    ProtocolErrorEvent,
    StartRoundBroadcastEvent,
    send_ws_message,
)

if TYPE_CHECKING:
    from app.ws_protocol import (
        CastKickVoteEvent,
        DrawpadClearEvent,
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
    )

logger = logging.getLogger(__name__)
LOBBY_PHASE = "lobby"


async def reject_if_not_host(session: WebSocketSessionContext, action: str) -> bool:
    """Reject host-only actions for non-host connections."""
    if session.is_host():
        return False
    logger.info("[Server] Ignored %s from non-host connection", action)
    await session.send_error("permission_error", "host_only", f"Only the host can {action}.")
    return True


async def handle_join(session: WebSocketSessionContext, event: JoinEvent) -> None:
    """Handle a join event for one websocket session."""
    try:
        _player, is_reconnecting_host = await session.room.add_player(event.player_id, event.name, session.websocket)
    except ValueError as exc:
        logger.warning("[Server] Player %s (%s) cannot join: %s", event.name, event.player_id, exc)
        await send_ws_message(
            session.websocket,
            ProtocolErrorEvent(type="join_error", error="room_full", message=str(exc)),
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


async def handle_start_game(session: WebSocketSessionContext, event: StartGameEvent) -> None:
    """Handle a start-game event."""
    if await reject_if_not_host(session, "start the game"):
        return
    if len(session.room.players) < 2 or session.room.metadata.game_phase != LOBBY_PHASE:
        return
    session.room.configure_game(
        round_length=event.round_length,
        difficulty=event.difficulty,
        max_rounds=event.rounds,
    )
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_start_round(session: WebSocketSessionContext, event: StartRoundEvent) -> None:
    """Handle a start-round event."""
    if await reject_if_not_host(session, "start a round"):
        return
    round_start_time = session.room.start_round(
        round_number=event.round,
        cards={
            player_id: card.model_dump(by_alias=True, exclude_none=True) for player_id, card in event.cards.items()
        },
    )
    await session.room.broadcast(
        StartRoundBroadcastEvent(
            type="start_round",
            round=event.round,
            cards=event.cards,
            roundStartTime=round_start_time,
        ),
    )
    await session.room.persist()


async def handle_player_ready(session: WebSocketSessionContext, event: PlayerReadyEvent) -> None:
    """Handle a player-ready event."""
    if event.player_id != session.player_id:
        await session.send_error("player_ready_error", "invalid_player", "Ready updates must match your connection.")
        return
    await session.room.broadcast(session.room.mark_player_ready(event.player_id))
    await session.room.persist()


async def handle_start_guessing(session: WebSocketSessionContext, event: StartGuessingEvent) -> None:
    """Handle a start-guessing event."""
    if await reject_if_not_host(session, "start guessing"):
        return
    session.room.start_scoring_timeout(session.room.start_guessing())
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_submit_guess(session: WebSocketSessionContext, event: SubmitGuessEvent) -> None:
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


async def handle_restart_game(session: WebSocketSessionContext, event: RestartGameEvent) -> None:
    """Handle a restart-game event."""
    if await reject_if_not_host(session, "restart the game"):
        return
    session.room.reset_game()
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_settings_update(session: WebSocketSessionContext, event: SettingsUpdateEvent) -> None:
    """Handle a settings-update event."""
    if await reject_if_not_host(session, "update room settings"):
        return
    session.room.metadata.difficulty = event.difficulty or session.room.metadata.difficulty
    session.room.metadata.max_rounds = event.rounds or session.room.metadata.max_rounds
    session.room.metadata.round_length = event.round_length or session.room.metadata.round_length
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_language_update(session: WebSocketSessionContext, event: LanguageUpdateEvent) -> None:
    """Handle a language-update event."""
    if await reject_if_not_host(session, "update room language"):
        return
    session.room.metadata.language = event.language
    await session.room.broadcast(LanguageUpdatedEvent(language=event.language))
    await session.room.persist()


async def handle_drawpad_clear(session: WebSocketSessionContext, event: DrawpadClearEvent) -> None:
    """Handle a drawpad-clear event."""
    if await reject_if_not_host(session, "clear the drawpad"):
        return
    await session.room.broadcast(event)


async def handle_pad_visibility(session: WebSocketSessionContext, event: PadVisibilityEvent) -> None:
    """Handle a pad-visibility event."""
    if await reject_if_not_host(session, "change pad visibility"):
        return
    session.room.metadata.pad_visibility = event.visible
    await session.room.broadcast(event)
    await session.room.persist()


async def handle_privacy_changed(session: WebSocketSessionContext, event: PrivacyChangedEvent) -> None:
    """Handle a privacy-changed event."""
    if await reject_if_not_host(session, "change room privacy"):
        return
    session.room.metadata.is_private = event.is_private
    await session.room.persist()


async def handle_initiate_kick(session: WebSocketSessionContext, event: InitiateKickEvent) -> None:
    """Handle initiating a kick vote."""
    if not session.player_id:
        return
    result = await session.room.initiate_kick_vote(session.player_id, event.target_player_id)
    if not result.success:
        await session.send_error("kick_error", result.error or "Failed to initiate kick vote", "")


async def handle_cast_kick_vote(session: WebSocketSessionContext, event: CastKickVoteEvent) -> None:
    """Handle casting a kick vote."""
    if not session.player_id:
        return
    result = await session.room.cast_kick_vote(session.player_id, event.target_player_id)
    if not result.success:
        await session.send_error("kick_error", result.error or "Failed to cast vote", "")


async def handle_request_game_state(session: WebSocketSessionContext, event: RequestGameStateEvent) -> None:
    """Handle a request-game-state event."""
    del event
    await send_ws_message(session.websocket, session.room.room_state_event())
