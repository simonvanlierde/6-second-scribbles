"""Room-related HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Query

from app.api_schemas import (
    CustomCategoryCreate,
    CustomCategoryCreateResponse,
    DeleteCustomCategoryResponse,
    RandomRoomResponse,
    RoomCategoriesResponse,
    RoomStatusResponse,
)
from app.database import AsyncSessionDep  # noqa: TC001 - FastAPI resolves this dependency alias at runtime
from app.services.room_service import (
    create_room_custom_category,
    delete_room_custom_category,
    get_random_joinable_room,
    get_room_status,
    list_room_categories,
)

router = APIRouter()


@router.get("/api/rooms/random", response_model=RandomRoomResponse)
async def get_random_room() -> RandomRoomResponse:
    """Find a random public room that's available to join."""
    return await get_random_joinable_room()


@router.post("/api/rooms/{room_id}/categories", response_model=CustomCategoryCreateResponse)
async def create_custom_category(
    room_id: str,
    category_data: CustomCategoryCreate,
    db: AsyncSessionDep,
) -> CustomCategoryCreateResponse:
    """Create a custom category for a specific room."""
    return await create_room_custom_category(db, room_id=room_id, category_data=category_data)


@router.get("/api/rooms/{room_id}/categories", response_model=RoomCategoriesResponse)
async def get_room_categories(room_id: str, db: AsyncSessionDep) -> RoomCategoriesResponse:
    """Get all custom categories for a specific room."""
    return await list_room_categories(db, room_id=room_id)


@router.delete("/api/rooms/{room_id}/categories/{category_id}", response_model=DeleteCustomCategoryResponse)
async def delete_custom_category(
    room_id: str,
    category_id: int,
    db: AsyncSessionDep,
    player_id_header: Annotated[str | None, Header(alias="X-Player-Id")] = None,
    player_id_query: Annotated[str | None, Query(alias="player_id")] = None,
) -> DeleteCustomCategoryResponse:
    """Delete a custom category from a room."""
    player_id = player_id_header or player_id_query
    return await delete_room_custom_category(db, room_id=room_id, category_id=category_id, player_id=player_id)


@router.get("/rooms/{room_id}/status", response_model=RoomStatusResponse, response_model_exclude_none=True)
async def room_status(room_id: str) -> RoomStatusResponse:
    """Get the status of a room."""
    return get_room_status(room_id=room_id)
