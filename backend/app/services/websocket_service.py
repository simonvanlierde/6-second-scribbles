"""WebSocket connection orchestration for room sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import WebSocketDisconnect

from app.game_room import room_manager
from app.websocket import RoomWebSocketSession

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def handle_room_websocket_connection(websocket: WebSocket, *, room_id: str) -> None:
    """Accept a websocket, run its room session, and clean it up on exit."""
    await websocket.accept()
    logger.info("[WebSocket] Connection accepted for room %s", room_id)

    room = room_manager.get_or_create_room(room_id)
    session = RoomWebSocketSession(room, websocket)

    try:
        await session.run()
    except WebSocketDisconnect:
        logger.info("[WebSocket] Client disconnected from room %s", room_id)
    except Exception:
        logger.exception("[WebSocket] Error in room %s", room_id)
    finally:
        await session.on_disconnect()
