"""WebSocket routes."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.services.websocket_service import handle_room_websocket_connection

router = APIRouter()


@router.websocket("/party/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    """WebSocket endpoint for game rooms."""
    await handle_room_websocket_connection(websocket, room_id=room_id)
