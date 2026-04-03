"""Room-related HTTP routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import select

from app.categories.models import Card, Category
from app.categories.schemas import CategorySummary
from app.core.config import settings
from app.core.database import AsyncSessionDep  # noqa: TC001 - FastAPI resolves this dependency alias at runtime
from app.rooms.manager import room_manager
from app.rooms.protocol import event_payload
from app.rooms.schemas import (
    CustomCategoryCreate,
    CustomCategoryCreateResponse,
    DeleteCustomCategoryResponse,
    RandomRoomResponse,
    RoomCategoriesItem,
    RoomCategoriesResponse,
    RoomStatusResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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


async def get_random_joinable_room() -> RandomRoomResponse:
    """Find a public room that can be joined."""
    room_code = room_manager.find_random_public_room(max_players=settings.max_players)

    if not room_code:
        raise HTTPException(status_code=404, detail="No available public rooms found. Try creating a new room!")

    room = room_manager.get_room(room_code)
    player_count = len(room.players) if room else 0
    return RandomRoomResponse(room_code=room_code, player_count=player_count, max_players=settings.max_players)


async def create_room_custom_category(
    db: AsyncSession,
    *,
    room_id: str,
    category_data: CustomCategoryCreate,
) -> CustomCategoryCreateResponse:
    """Create a room-specific custom category and broadcast it."""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.host_id != category_data.created_by:
        raise HTTPException(status_code=403, detail="Only the room host can create custom categories")

    if len(category_data.items) < 5:
        raise HTTPException(status_code=400, detail="Custom category must have at least 5 items")

    category = Category(
        name=category_data.name,
        difficulty=category_data.difficulty,
        description=category_data.description or f"Custom category for room {room_id}",
        room_id=room_id,
        created_by=category_data.created_by,
    )
    db.add(category)
    await db.flush()

    for item in category_data.items:
        db.add(Card(category_id=category.id, item=item.strip(), alternatives=[]))

    await db.commit()

    category_summary = CategorySummary.from_model(category)
    await room.broadcast(
        event_payload("custom_category_added", category=category_summary.model_dump(), items=category_data.items),
    )

    return CustomCategoryCreateResponse(
        success=True,
        category=category_summary,
        message=f"Custom category '{category_data.name}' created with {len(category_data.items)} items",
    )


async def list_room_categories(db: AsyncSession, *, room_id: str) -> RoomCategoriesResponse:
    """List all custom categories for a room."""
    result = await db.execute(select(Category).where(Category.room_id == room_id))
    categories = result.scalars().all()

    category_ids = [category.id for category in categories]
    cards_by_cat: dict[int, list[str]] = {}
    if category_ids:
        cards_result = await db.execute(select(Card).where(Card.category_id.in_(category_ids)))
        for card in cards_result.scalars().all():
            cards_by_cat.setdefault(card.category_id, []).append(card.item)

    categories_with_items = [
        RoomCategoriesItem.from_model(category, items=cards_by_cat.get(category.id, [])) for category in categories
    ]

    return RoomCategoriesResponse(room_id=room_id, categories=categories_with_items, count=len(categories_with_items))


async def delete_room_custom_category(
    db: AsyncSession,
    *,
    room_id: str,
    category_id: int,
    player_id: str | None,
) -> DeleteCustomCategoryResponse:
    """Delete a room-specific custom category and broadcast it."""
    if not player_id:
        raise HTTPException(status_code=422, detail="Player ID is required")

    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only the room host can delete custom categories")

    result = await db.execute(select(Category).where(Category.id == category_id, Category.room_id == room_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Custom category not found")

    await db.delete(category)
    await db.commit()

    await room.broadcast(
        event_payload("custom_category_removed", category_id=category_id, category_name=category.name),
    )

    return DeleteCustomCategoryResponse(success=True, message=f"Custom category '{category.name}' deleted")


def get_room_status(*, room_id: str) -> RoomStatusResponse:
    """Return the current status for a room."""
    room = room_manager.get_room(room_id)
    if not room:
        return RoomStatusResponse(exists=False)

    return RoomStatusResponse(exists=True, players=len(room.players), game_phase=room.metadata.game_phase)
