"""Player join/leave and host-transfer helpers for game rooms."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.core.avatar import AVATAR_COLOR_TOKENS, pick_avatar_color
from app.rooms.protocol import HostChangedEvent

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import WebSocket

    from app.rooms.manager import GameRoom, PlayerInfo

logger = logging.getLogger(__name__)

# Sentinel raised by add_player when a player_id is claimed by a different user;
# handle_join matches on it to send the right join error.
IDENTITY_CONFLICT_ERROR = "identity_conflict"


async def add_player(
    room: GameRoom,
    player_id: str,
    name: str,
    websocket: WebSocket,
    *,
    preferred_locale: str | None = None,
    user_id: str | None = None,
    preferred_color: str | None = None,
    max_players: int,
    player_info_factory: type[PlayerInfo],
) -> tuple[PlayerInfo, bool]:
    """Add or replace a player connection and report whether this restored the host."""
    if player_id not in room.players and len(room.players) >= max_players:
        msg = f"Room is full (maximum {max_players} players)"
        raise ValueError(msg)

    # Bind player identity to the authenticated session: a player_id already
    # owned by one user cannot be claimed by a connection authenticated as a
    # different user. This blocks seat/host takeover via a spoofed player_id.
    existing_owner = room.metadata.player_user_ids.get(player_id)
    if existing_owner is not None and existing_owner != user_id:
        raise ValueError(IDENTITY_CONFLICT_ERROR)

    if room.is_hibernated:
        logger.info("[GameRoom %s] Waking from hibernation", room.room_id)
        room.is_hibernated = False

    room.last_activity = time.time()
    room.emptied_at = None

    is_reconnecting_host = (
        player_id == room.last_host_id and player_id not in room.players and _owns_last_host(room, user_id)
    )

    # Reuse an existing player's colour on reconnect; otherwise prefer the
    # client-supplied colour if valid; otherwise pick one not taken by another
    # player in the room.
    existing = room.players.get(player_id)
    if existing is not None and existing.color:
        color = existing.color
    elif preferred_color and preferred_color in AVATAR_COLOR_TOKENS:
        color = preferred_color
    else:
        used = [p.color for p in room.players.values() if p.color and p.id != player_id]
        color = pick_avatar_color(player_id, used)

    player = player_info_factory(
        id=player_id,
        name=name,
        websocket=websocket,
        last_activity=time.time(),
        color=color,
        connected=True,
    )
    room.players[player_id] = player
    # Assign a stable seat on first join; reconnects keep their original slot so
    # the roster order is preserved for everyone.
    if player_id not in room.metadata.player_seats:
        room.metadata.player_seats[player_id] = (
            (max(room.metadata.player_seats.values()) + 1) if room.metadata.player_seats else 0
        )
    room.metadata.player_locales[player_id] = preferred_locale or room.metadata.default_locale
    if user_id is not None:
        room.metadata.player_user_ids[player_id] = user_id
    else:
        room.metadata.player_user_ids.pop(player_id, None)

    _settle_host_on_join(room, player_id, name, user_id=user_id, is_reconnecting_host=is_reconnecting_host)
    return player, is_reconnecting_host


def _owns_last_host(room: GameRoom, user_id: str | None) -> bool:
    """Return whether `user_id` is the authenticated owner of the last host.

    A `None` recorded owner (e.g. a fully anonymous host) cannot be proven, so it
    is treated as ownerless and reclaimable to preserve legacy behaviour.
    """
    return room.last_host_user_id is None or room.last_host_user_id == user_id


def _settle_host_on_join(
    room: GameRoom,
    player_id: str,
    name: str,
    *,
    user_id: str | None,
    is_reconnecting_host: bool,
) -> None:
    """Reclaim host for a returning last-host, or assign it to a lone first player.

    Restoring on any (re)join by the last known host is order-independent, unlike
    `is_reconnecting_host`, which only holds when the old socket was already gone.

    Host reclaim is gated on identity: only the authenticated owner of the prior
    host may reclaim it, so a different user presenting the old host's player_id
    is treated as an ordinary joining player rather than seizing the role.
    """
    is_last_host = player_id == room.last_host_id
    if is_last_host and _owns_last_host(room, user_id):
        if room.pending_host_transfer:
            room.pending_host_transfer.cancel()
            room.pending_host_transfer = None
        room.host_id = player_id
        if is_reconnecting_host:
            logger.info(
                "[GameRoom %s] Host %s (%s) reconnected, host transfer cancelled",
                room.room_id,
                name,
                player_id,
            )
    elif is_last_host:
        # A different authenticated user is reusing the prior host's freed
        # player_id. Never let them inherit a lingering host_id; leave the reclaim
        # markers intact so the real host can still return, and let any pending
        # transfer promote a present player instead.
        if room.host_id == player_id:
            room.host_id = None
    elif len(room.players) == 1:
        room.host_id = player_id
        room.last_host_id = player_id
        room.last_host_user_id = user_id


async def remove_player(
    room: GameRoom,
    player_id: str,
    *,
    host_transfer_delay_ms: int,
    schedule_host_transfer: Callable[[str], asyncio.Task[object]],
) -> None:
    """Remove a player and trigger delayed host transfer when required."""
    room.players.pop(player_id, None)
    room.metadata.player_locales.pop(player_id, None)
    room.metadata.player_user_ids.pop(player_id, None)
    # Forget all per-player round state so a removed player (left/kicked/pruned)
    # is no longer treated as a current participant. In particular this drops them
    # from player_assignments, which the rejoin gate uses to recognise reconnecting
    # participants — without it a kicked player could rejoin the active round.
    room.metadata.player_assignments.pop(player_id, None)
    room.metadata.guess_targets.pop(player_id, None)
    room.metadata.submitted_players.discard(player_id)
    room.metadata.ready_players.discard(player_id)
    room.metadata.player_seats.pop(player_id, None)

    # Drop any kick vote targeting the leaver (otherwise it lingers with its
    # accumulated voters and would kick them the instant they rejoin) and remove
    # them from every other vote's voter set so departed players can't count
    # toward a threshold.
    room.active_kick_votes.pop(player_id, None)
    for vote in room.active_kick_votes.values():
        vote.voters.discard(player_id)

    if room.is_empty():
        room.emptied_at = time.time()
        logger.info("[GameRoom %s] Room is now empty, marked for hibernation/cleanup", room.room_id)

    if player_id != room.host_id:
        return

    if room.players:
        logger.info(
            "[GameRoom %s] Host disconnected, scheduling transfer in %sms...",
            room.room_id,
            host_transfer_delay_ms,
        )
        if room.pending_host_transfer:
            room.pending_host_transfer.cancel()
        room.pending_host_transfer = schedule_host_transfer(player_id)
        return

    room.host_id = None
    room.last_host_id = None
    room.last_host_user_id = None


async def delayed_host_transfer(room: GameRoom, old_host_id: str, *, host_transfer_delay_ms: int) -> None:
    """Transfer host after a delay, allowing time for reconnection."""
    try:
        await asyncio.sleep(host_transfer_delay_ms / 1000)

        old_host = room.players.get(old_host_id)
        if old_host is not None and old_host.connected and _owns_last_host(room, room.get_player_user_id(old_host_id)):
            logger.info("[GameRoom %s] Host reconnected, cancelling transfer", room.room_id)
            room.host_id = old_host_id
            return

        new_host = next((player for player in room.players.values() if player.connected), None)
        if new_host is not None:
            room.host_id = new_host.id
            room.last_host_id = new_host.id
            room.last_host_user_id = room.get_player_user_id(new_host.id)
            await room.broadcast(HostChangedEvent(newHostId=new_host.id))
            logger.info("[GameRoom %s] Host transferred to %s (%s)", room.room_id, new_host.name, new_host.id)
            return

        room.host_id = None
        room.last_host_id = None
        room.last_host_user_id = None
    except asyncio.CancelledError:
        logger.info("[GameRoom %s] Host transfer cancelled (host reconnected)", room.room_id)
    finally:
        # Only clear the field if it still points at *this* task. A cancelled
        # transfer may have already been replaced by a newer one; nulling it
        # unconditionally would orphan that replacement.
        if room.pending_host_transfer is asyncio.current_task():
            room.pending_host_transfer = None


def update_player_activity(room: GameRoom, player_id: str) -> None:
    """Update the last activity timestamp for a player."""
    if player_id in room.players:
        room.players[player_id].last_activity = time.time()


def is_host(room: GameRoom, player_id: str | None) -> bool:
    """Return whether the given player currently owns the room."""
    return bool(player_id and room.host_id and player_id == room.host_id)
