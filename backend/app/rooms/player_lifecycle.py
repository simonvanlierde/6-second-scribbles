"""Player join/leave and host-transfer helpers for game rooms."""
# ruff: noqa: SLF001

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.rooms.protocol import HostChangedEvent

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import WebSocket

    from app.rooms.manager import GameRoom, PlayerInfo

logger = logging.getLogger(__name__)


async def add_player(
    room: GameRoom,
    player_id: str,
    name: str,
    websocket: WebSocket,
    *,
    max_players: int,
    player_info_factory: type[PlayerInfo],
) -> tuple[PlayerInfo, bool]:
    """Add or replace a player connection and report whether this restored the host."""
    if player_id not in room.players and len(room.players) >= max_players:
        msg = f"Room is full (maximum {max_players} players)"
        raise ValueError(msg)

    if room.is_hibernated:
        logger.info("[GameRoom %s] Waking from hibernation", room.room_id)
        room.is_hibernated = False

    room._last_activity = time.time()
    room._emptied_at = None

    is_reconnecting_host = player_id == room._last_host_id and player_id not in room.players
    player = player_info_factory(
        id=player_id,
        name=name,
        websocket=websocket,
        last_activity=time.time(),
    )
    room.players[player_id] = player

    if is_reconnecting_host and room._pending_host_transfer:
        room._pending_host_transfer.cancel()
        room._pending_host_transfer = None
        room.host_id = player_id
        logger.info(
            "[GameRoom %s] Host %s (%s) reconnected, host transfer cancelled",
            room.room_id,
            name,
            player_id,
        )
    elif len(room.players) == 1:
        room.host_id = player_id
        room._last_host_id = player_id

    return player, is_reconnecting_host


async def remove_player(
    room: GameRoom,
    player_id: str,
    *,
    host_transfer_delay_ms: int,
    schedule_host_transfer: Callable[[str], asyncio.Task[object]],
) -> None:
    """Remove a player and trigger delayed host transfer when required."""
    room.players.pop(player_id, None)

    if room.is_empty():
        room._emptied_at = time.time()
        logger.info("[GameRoom %s] Room is now empty, marked for hibernation/cleanup", room.room_id)

    if player_id != room.host_id:
        return

    if room.players:
        logger.info(
            "[GameRoom %s] Host disconnected, scheduling transfer in %sms...",
            room.room_id,
            host_transfer_delay_ms,
        )
        if room._pending_host_transfer:
            room._pending_host_transfer.cancel()
        room._pending_host_transfer = schedule_host_transfer(player_id)
        return

    room.host_id = None
    room._last_host_id = None


async def delayed_host_transfer(room: GameRoom, old_host_id: str, *, host_transfer_delay_ms: int) -> None:
    """Transfer host after a delay, allowing time for reconnection."""
    try:
        await asyncio.sleep(host_transfer_delay_ms / 1000)

        if old_host_id in room.players:
            logger.info("[GameRoom %s] Host reconnected, cancelling transfer", room.room_id)
            room.host_id = old_host_id
            return

        if room.players:
            new_host = next(iter(room.players.values()))
            room.host_id = new_host.id
            room._last_host_id = new_host.id
            await room.broadcast(HostChangedEvent(newHostId=new_host.id))
            logger.info("[GameRoom %s] Host transferred to %s (%s)", room.room_id, new_host.name, new_host.id)
            return

        room.host_id = None
        room._last_host_id = None
    except asyncio.CancelledError:
        logger.info("[GameRoom %s] Host transfer cancelled (host reconnected)", room.room_id)
    finally:
        room._pending_host_transfer = None


def update_player_activity(room: GameRoom, player_id: str) -> None:
    """Update the last activity timestamp for a player."""
    if player_id in room.players:
        room.players[player_id].last_activity = time.time()


def is_host(room: GameRoom, player_id: str | None) -> bool:
    """Return whether the given player currently owns the room."""
    return bool(player_id and room.host_id and player_id == room.host_id)
