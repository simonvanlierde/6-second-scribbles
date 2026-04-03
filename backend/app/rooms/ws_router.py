"""WebSocket routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.rooms.manager import room_manager
from app.rooms.session import RoomWebSocketSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/party/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket endpoint for game rooms."""
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
