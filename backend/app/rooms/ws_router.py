"""WebSocket routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.service import get_user_by_session
from app.core.config import settings
from app.core.database import get_session_maker
from app.rooms.manager import room_manager
from app.rooms.session import RoomWebSocketSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["rooms"])


@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket endpoint for game rooms."""
    await websocket.accept()
    logger.info("[WebSocket] Connection accepted for room %s", room_id)

    room = room_manager.get_or_create_room(room_id)
    session_maker = get_session_maker()
    session_id = websocket.cookies.get(settings.session_cookie_name)
    async with session_maker() as db:
        current_user = await get_user_by_session(db, session_id)
    session = RoomWebSocketSession(room, websocket, current_user=current_user)

    try:
        await session.run()
    except WebSocketDisconnect:
        logger.info("[WebSocket] Client disconnected from room %s", room_id)
    except RuntimeError, ValueError, TypeError, OSError:
        # Network/runtime errors — log and clean up via `finally`. Assertion
        # and cancellation errors still propagate for test/shutdown integrity.
        logger.exception("[WebSocket] Unexpected error in room %s", room_id)
    finally:
        await session.on_disconnect()
