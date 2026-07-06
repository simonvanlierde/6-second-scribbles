"""Room-related HTTP routes."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request

from app.categories.schemas import CategorySelectionRequest, CategorySelectionResponse
from app.categories.service import select_category_sets
from app.core.config import settings
from app.core.database import AsyncSessionDep
from app.core.rate_limits import enforce_rate_limit, get_client_identifier
from app.core.redis import get_redis
from app.rooms.manager import RoomCapacityError, room_manager
from app.rooms.schemas import (
    CreateRoomResponse,
    QuickPlayResponse,
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

    requested_locales = request.locales or [room.get_player_locale(player_id) for player_id in room.players]

    return await select_category_sets(
        db,
        difficulty=request.difficulty,
        count=request.count,
        player_count=request.player_count,
        locale=request.locale,
        locales=requested_locales,
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
async def create_room(request: Request) -> CreateRoomResponse:
    """Create a new room with a unique alphanumeric code and reserve it in Redis.

    This endpoint attempts several times to generate a code and atomically set the
    Redis key so multiple server instances won't collide. On success it creates
    the in-memory room and persists initial state.
    """
    await _enforce_room_creation_limit(request)
    code = await _reserve_new_room_code()
    return CreateRoomResponse(room_code=code)


@router.post("/quick-play", response_model=QuickPlayResponse)
async def quick_play(request: Request) -> QuickPlayResponse:
    """Return a joinable public room, creating one if none are available.

    Intended for the Home screen's one-tap "Quick-play" action: pick a random
    public room in the lobby phase with room left, or create a fresh one.
    """
    await _enforce_room_creation_limit(request)
    existing = room_manager.find_random_public_room(max_players=settings.max_players)
    if existing:
        return QuickPlayResponse(room_code=existing, kind="existing")

    code = await _reserve_new_room_code()
    return QuickPlayResponse(room_code=code, kind="created")


async def _enforce_room_creation_limit(request: Request) -> None:
    """Apply the per-IP room-creation rate limit."""
    await enforce_rate_limit(
        bucket="room_creation",
        identifier=get_client_identifier(request),
        limit=settings.room_creation_rate_limit,
        window_seconds=settings.room_creation_rate_window_seconds,
    )


async def _reserve_new_room_code() -> str:
    """Reserve a unique room code in Redis and create the in-memory room."""
    r = await get_redis()
    attempts = 10
    for _ in range(attempts):
        code = "".join(secrets.choice(ALLOWED_CHARS) for _ in range(ROOM_CODE_LENGTH))
        key = f"room:{code}"
        state = RoomState(room_id=code)
        value = state.model_dump_json()
        ok = await r.set(key, value, nx=True, ex=settings.room_ttl_seconds)
        if ok:
            # Any failure after the reserve must release the code, or it lingers
            # for the full TTL with no room behind it (status reports exists=False
            # while Redis still considers the code taken).
            try:
                room = room_manager.get_or_create_room(code)
                await room.persist()
            except RoomCapacityError as exc:
                await r.delete(key)
                raise HTTPException(
                    status_code=503,
                    detail="Server is at capacity. Please try again shortly.",
                    headers={"Retry-After": "30"},
                ) from exc
            except Exception:
                await r.delete(key)
                raise
            return code

    raise HTTPException(status_code=500, detail="Failed to generate unique room code. Try again.")
