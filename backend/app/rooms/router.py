"""Room-related HTTP routes."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException

from app.categories.schemas import CategorySelectionRequest, CategorySelectionResponse
from app.categories.service import select_category_sets
from app.core.config import settings
from app.core.database import AsyncSessionDep  # noqa: TC001 - FastAPI resolves this dependency alias at runtime
from app.core.redis import get_redis
from app.rooms.manager import room_manager
from app.rooms.schemas import (
    CreateRoomResponse,
    RandomRoomResponse,
    RoomStatusResponse,
)
from app.rooms.state import RoomState

# spell-checker: ignore setnx

ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
ROOM_CODE_LENGTH = 6

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/random", response_model=RandomRoomResponse)
async def get_random_room() -> RandomRoomResponse:
    """Find a random public room that's available to join."""
    return await get_random_joinable_room()


@router.get("/{room_id}/status", response_model=RoomStatusResponse, response_model_exclude_none=True)
async def room_status(room_id: str) -> RoomStatusResponse:
    """Get the status of a room."""
    return get_room_status(room_id=room_id)


@router.post("/{room_id}/category-selection", response_model=CategorySelectionResponse)
async def select_room_categories(
    room_id: str,
    request: CategorySelectionRequest,
    db: AsyncSessionDep,
) -> CategorySelectionResponse:
    """Select category sets for a specific room/game setup."""
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    requested_locales = request.locales or [room.get_player_locale(player_id) for player_id in room.players.keys()]

    return await select_category_sets(
        db,
        room_id=room_id,
        difficulty=request.difficulty,
        count=request.count,
        player_count=request.player_count,
        locale=request.locale,
        locales=requested_locales,
        owner_user_id=room.get_host_owner_user_id(),
        enabled_custom_category_ids=room.metadata.custom_category_ids,
    )


async def get_random_joinable_room() -> RandomRoomResponse:
    """Find a public room that can be joined."""
    room_code = room_manager.find_random_public_room(max_players=settings.max_players)

    if not room_code:
        raise HTTPException(status_code=404, detail="No available public rooms found. Try creating a new room!")

    room = room_manager.get_room(room_code)
    player_count = len(room.players) if room else 0
    return RandomRoomResponse(room_code=room_code, player_count=player_count, max_players=settings.max_players)


def get_room_status(*, room_id: str) -> RoomStatusResponse:
    """Return the current status for a room."""
    room = room_manager.get_room(room_id)
    if not room:
        return RoomStatusResponse(exists=False)

    return RoomStatusResponse(exists=True, players=len(room.players), game_phase=room.metadata.game_phase)


@router.post("/", response_model=CreateRoomResponse)
async def create_room() -> CreateRoomResponse:
    """Create a new room with a unique alphanumeric code and reserve it in Redis.

    This endpoint attempts several times to generate a code and atomically set the
    Redis key so multiple server instances won't collide. On success it creates
    the in-memory room and persists initial state.
    """
    r = await get_redis()
    attempts = 10
    for _ in range(attempts):
        code = "".join(secrets.choice(ALLOWED_CHARS) for _ in range(ROOM_CODE_LENGTH))
        key = f"room:{code}"

        # Prepare an initial RoomState JSON so the key contains a valid persisted value
        state = RoomState(room_id=code)
        value = state.model_dump_json()

        # Try to atomically set the key only if it doesn't exist
        # redis-py returns True when successful
        ok = await r.set(key, value, nx=True, ex=settings.room_ttl_seconds)
        if ok:
            # Reserve succeeded. Create in-memory room and persist canonical state
            room = room_manager.get_or_create_room(code)
            await room.persist()
            return CreateRoomResponse(room_code=code)

    raise HTTPException(status_code=500, detail="Failed to generate unique room code. Try again.")
