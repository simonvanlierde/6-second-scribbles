"""WebSocket routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.auth.service import get_user_by_session
from app.core.config import settings
from app.core.database import get_session_maker
from app.core.rate_limits import enforce_rate_limit, get_client_identifier
from app.rooms.manager import RoomCapacityError, room_manager
from app.rooms.session import RoomWebSocketSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["rooms"])


@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket endpoint for game rooms."""
    await websocket.accept()
    logger.info("[WebSocket] Connection accepted for room %s", room_id)

    # Connecting to a code that has no room yet creates one. Apply the same per-IP
    # limit as POST /rooms so an unauthenticated client can't exhaust the global
    # room pool by opening sockets to arbitrary codes.
    if room_manager.get_room(room_id) is None:
        try:
            await enforce_rate_limit(
                bucket="room_creation",
                identifier=get_client_identifier(websocket),
                limit=settings.room_creation_rate_limit,
                window_seconds=settings.room_creation_rate_window_seconds,
            )
        except HTTPException:
            logger.warning("[WebSocket] Room %s creation rejected: rate limited", room_id)
            await websocket.close(code=1013, reason="Rate limit exceeded")
            return

    try:
        room = room_manager.get_or_create_room(room_id)
    except RoomCapacityError:
        logger.warning("[WebSocket] Room %s rejected: server at capacity", room_id)
        await websocket.close(code=1013, reason="Server at capacity")
        return

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
