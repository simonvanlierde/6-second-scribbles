"""FastAPI Server for Six Second Scribbles.

Architecture: "Dumb Pipe" Pattern
- Server only relays messages between clients
- All game logic lives in client-side GameEngine
- Migrated from PartyKit for better scalability
"""

import json
import logging
import random
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.database import close_db, get_db, init_db
from app.db_models import Card, Category
from app.game_room import room_manager
from app.redis_store import close_redis, get_redis
from app.scoring import guess_matcher
from app.ws_handler import WSMessageHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# Pydantic models for request/response
class GuessRequest(BaseModel):
    guesses: list[str]
    correct_answers: list[str]
    alternatives: dict = {}


class GuessResponse(BaseModel):
    score: int
    total: int
    percentage: float
    matches: list[dict]
    unmatched_answers: list[str]


class CustomCategoryCreate(BaseModel):
    name: str
    items: list[str]  # List of items for this category
    difficulty: str = "medium"
    description: str | None = None
    created_by: str  # Player ID


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown logic."""
    # Startup
    logger.info("Starting Six Second Scribbles API...")
    await init_db()
    logger.info("Database initialized")

    try:
        await get_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis unavailable — room state will not persist across restarts: %s", e)

    await room_manager.start()
    logger.info("Room manager started")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await room_manager.stop()
    logger.info("Room manager stopped")

    await close_db()
    logger.info("Database connections closed")

    await close_redis()
    logger.info("Redis connection closed")


app = FastAPI(
    title="Six Second Scribbles API",
    description="Real-time multiplayer drawing game backend",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "Six Second Scribbles API", "version": "2.0.0"}


@app.get("/api/stats")
async def get_stats() -> dict[str, Any]:
    """Get server statistics including room counts and player counts.

    Returns room manager stats like total rooms, active rooms, hibernated rooms, etc.
    """
    stats = room_manager.get_stats()
    return {"status": "ok", **stats}


@app.get("/api/rooms/random")
async def get_random_room() -> dict[str, Any]:
    """Find a random public room that's available to join.

    Returns:
    - room_code: The room code to join
    - player_count: Current number of players in the room

    Returns 404 if no available rooms found
    """
    room_code = room_manager.find_random_public_room(max_players=settings.max_players)

    if not room_code:
        raise HTTPException(status_code=404, detail="No available public rooms found. Try creating a new room!")

    room = room_manager.get_room(room_code)
    player_count = len(room.players) if room else 0

    return {"room_code": room_code, "player_count": player_count, "max_players": settings.max_players}


@app.get("/api/categories")
async def get_categories(
    difficulty: str | None = None,
    language: str | None = "en",
    db: AsyncSession = Depends(get_db),
):
    """Get all categories, optionally filtered by difficulty and language.

    Query params:
        difficulty: Filter by difficulty (easy, medium, hard)
        language: Filter by language (en, es, fr, etc.) - defaults to 'en'
    """
    query = select(Category)

    if difficulty:
        query = query.where(Category.difficulty == difficulty.lower())

    if language:
        query = query.where(Category.language == language.lower())

    result = await db.execute(query)
    categories = result.scalars().all()

    return {"categories": [cat.to_dict() for cat in categories], "count": len(categories)}


@app.get("/api/categories/{category_id}")
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific category with its items"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get cards for this category
    cards_result = await db.execute(select(Card).where(Card.category_id == category_id))
    cards = cards_result.scalars().all()

    return {
        "category": category.to_dict(),
        "items": [card.item for card in cards],
        "cards": [card.to_dict() for card in cards],
    }


@app.get("/api/cards/random")
async def get_random_cards(
    difficulty: str = "medium",
    count: int = 1,
    player_count: int = 2,
    room_id: str | None = None,  # Include room-specific categories
    language: str = "en",  # Language filter
    db: AsyncSession = Depends(get_db),
):
    """Get random cards for a game

    Query params:
        difficulty: Difficulty level (easy, medium, hard)
        count: Number of rounds (cards per player)
        player_count: Number of players
        room_id: If provided, includes custom categories for this room
        language: Language code (en, es, fr, etc.) - defaults to 'en'

    Returns unique categories for each player for each round
    """
    # Build query for global categories with this difficulty and language
    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.language == language.lower(),
        Category.room_id.is_(None),  # Global categories only
    )
    result = await db.execute(query)
    categories = list(result.scalars().all())

    # If room_id provided, also include custom categories for that room
    # Note: Room-specific categories use the room's language setting
    if room_id:
        custom_query = select(Category).where(Category.room_id == room_id)
        custom_result = await db.execute(custom_query)
        custom_categories = list(custom_result.scalars().all())
        categories.extend(custom_categories)

    if not categories:
        raise HTTPException(status_code=404, detail=f"No categories found for difficulty: {difficulty}")

    total_needed = count * player_count

    if len(categories) < total_needed:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough categories ({len(categories)}) for {player_count} players and {count} rounds. "
            f"Available: {len(categories)}, needed: {total_needed}",
        )

    # Randomly select categories without replacement
    selected_categories = random.sample(categories, total_needed)

    # Fetch all cards for selected categories in a single query
    selected_ids = [c.id for c in selected_categories]
    all_cards_result = await db.execute(select(Card).where(Card.category_id.in_(selected_ids)))
    cards_by_cat_id: dict[int, list[Card]] = {}
    for card in all_cards_result.scalars().all():
        cards_by_cat_id.setdefault(card.category_id, []).append(card)

    cards_by_category = {}
    for category in selected_categories:
        cards = cards_by_cat_id.get(category.id, [])
        cards_by_category[category.id] = {
            "category": category.name,
            "items": [card.item for card in cards],
            "alternatives": {card.item: card.alternatives for card in cards},
            "is_custom": category.room_id is not None,
        }

    return {"difficulty": difficulty, "categories": cards_by_category, "includes_custom": room_id is not None}


@app.post("/api/score/guesses", response_model=GuessResponse)
async def score_guesses(request: GuessRequest):
    """Score player guesses using fuzzy matching

    Body:
        guesses: List of player's guesses
        correct_answers: List of correct answers
        alternatives: Dict mapping answers to alternative spellings
    """
    result = guess_matcher.score_guesses(
        guesses=request.guesses,
        correct_answers=request.correct_answers,
        alternatives_map=request.alternatives,
    )

    return GuessResponse(**result)


# Custom Categories (Room-specific)
@app.post("/api/rooms/{room_id}/categories")
async def create_custom_category(room_id: str, category_data: CustomCategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a custom category for a specific room

    Only available for the host of that room during the game session.
    Custom categories are automatically cleaned up when the room closes.
    """
    # Verify room exists
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify the creator is the host
    if room.host_id != category_data.created_by:
        raise HTTPException(status_code=403, detail="Only the room host can create custom categories")

    # Validate items count (should have at least 5, typically 10)
    if len(category_data.items) < 5:
        raise HTTPException(status_code=400, detail="Custom category must have at least 5 items")

    # Create category
    category = Category(
        name=category_data.name,
        difficulty=category_data.difficulty,
        description=category_data.description or f"Custom category for room {room_id}",
        room_id=room_id,
        created_by=category_data.created_by,
    )
    db.add(category)
    await db.flush()  # Get the category ID

    # Create cards for this category
    for item in category_data.items:
        card = Card(category_id=category.id, item=item.strip(), alternatives=[])
        db.add(card)

    await db.commit()

    # Broadcast to all players in room
    await room.broadcast(
        {"type": "custom_category_added", "category": category.to_dict(), "items": category_data.items},
    )

    return {
        "success": True,
        "category": category.to_dict(),
        "message": f"Custom category '{category_data.name}' created with {len(category_data.items)} items",
    }


@app.get("/api/rooms/{room_id}/categories")
async def get_room_categories(room_id: str, db: AsyncSession = Depends(get_db)):
    """Get all custom categories for a specific room

    Returns only the categories created for this room, not global categories.
    """
    result = await db.execute(select(Category).where(Category.room_id == room_id))
    categories = result.scalars().all()

    # Fetch all cards for all categories in a single query
    category_ids = [cat.id for cat in categories]
    cards_by_cat: dict[int, list[str]] = {}
    if category_ids:
        cards_result = await db.execute(select(Card).where(Card.category_id.in_(category_ids)))
        for card in cards_result.scalars().all():
            cards_by_cat.setdefault(card.category_id, []).append(card.item)

    categories_with_items = [
        {**category.to_dict(), "items": cards_by_cat.get(category.id, [])} for category in categories
    ]

    return {"room_id": room_id, "categories": categories_with_items, "count": len(categories_with_items)}


@app.delete("/api/rooms/{room_id}/categories/{category_id}")
async def delete_custom_category(
    room_id: str,
    category_id: int,
    player_id_header: str | None = Header(default=None, alias="X-Player-Id"),
    player_id_query: str | None = Query(default=None, alias="player_id"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom category from a room

    Only the host can delete custom categories.
    """
    # Accept either the current header-based auth or the legacy query param.
    player_id = player_id_header or player_id_query
    if not player_id:
        raise HTTPException(status_code=422, detail="Player ID is required")

    # Verify room exists
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify the player is the host
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only the room host can delete custom categories")

    # Get category
    result = await db.execute(select(Category).where(Category.id == category_id, Category.room_id == room_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Custom category not found")

    # Delete category (cards will cascade delete)
    await db.delete(category)
    await db.commit()

    # Broadcast to all players in room
    await room.broadcast(
        {"type": "custom_category_removed", "category_id": category_id, "category_name": category.name},
    )

    return {"success": True, "message": f"Custom category '{category.name}' deleted"}


@app.get("/rooms/{room_id}/status")
async def room_status(room_id: str):
    """Get the status of a room"""
    room = room_manager.get_room(room_id)
    if not room:
        return {"exists": False}

    return {
        "exists": True,
        "players": len(room.players),
        "game_phase": room.metadata.game_phase,
    }


@app.websocket("/party/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for game rooms"""
    await websocket.accept()
    logger.info("[WebSocket] Connection accepted for room %s", room_id)

    room = room_manager.get_or_create_room(room_id)
    handler = WSMessageHandler(room, websocket)

    try:
        # Send initial room state
        await websocket.send_text(
            json.dumps(
                {
                    "type": "room_state",
                    "players": room.get_player_list(),
                    "hostId": room.host_id,
                    "categories": room.metadata.categories,
                    "gamePhase": room.metadata.game_phase,
                    "roundStartTime": room.metadata.round_start_time,
                    "roundLength": room.metadata.round_length,
                    "difficulty": room.metadata.difficulty,
                    "maxRounds": room.metadata.max_rounds,
                    "padVisibility": room.metadata.pad_visibility,
                    "language": room.metadata.language,
                },
            ),
        )

        # Handle messages
        while True:
            data = await websocket.receive_text()
            await handler.handle(data)

    except WebSocketDisconnect:
        logger.info("[WebSocket] Client disconnected from room %s", room_id)
    except Exception:
        logger.exception("[WebSocket] Error in room %s", room_id)
    finally:
        # Clean up player using the handler's cached player_id
        player_id = handler._player_id
        if player_id and room:
            await room.remove_player(player_id)
            await room.broadcast({"type": "player_left", "playerId": player_id})
            await room.persist()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
