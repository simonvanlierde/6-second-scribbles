"""FastAPI Server for Six Second Scribbles.

Architecture: "Dumb Pipe" Pattern
- Server only relays messages between clients
- All game logic lives in client-side GameEngine
- Migrated from PartyKit for better scalability
"""

import json
import logging
import random
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import close_db, get_db, init_db
from app.db_models import Card, Category
from app.game_room import room_manager
from app.redis_store import close_redis, get_redis
from app.scoring import guess_matcher

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
    room_code = room_manager.find_random_public_room(max_players=10)

    if not room_code:
        raise HTTPException(status_code=404, detail="No available public rooms found. Try creating a new room!")

    room = room_manager.get_room(room_code)
    player_count = len(room.players) if room else 0

    return {"room_code": room_code, "player_count": player_count, "max_players": 10}


@app.get("/api/categories")
async def get_categories(
    difficulty: str | None = None, language: str | None = "en", db: AsyncSession = Depends(get_db)
):
    """Get all categories, optionally filtered by difficulty and language

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
        guesses=request.guesses, correct_answers=request.correct_answers, alternatives_map=request.alternatives
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
        {"type": "custom_category_added", "category": category.to_dict(), "items": category_data.items}
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

    # Get cards for each category
    categories_with_items = []
    for category in categories:
        cards_result = await db.execute(select(Card).where(Card.category_id == category.id))
        cards = cards_result.scalars().all()

        categories_with_items.append({**category.to_dict(), "items": [card.item for card in cards]})

    return {"room_id": room_id, "categories": categories_with_items, "count": len(categories_with_items)}


@app.delete("/api/rooms/{room_id}/categories/{category_id}")
async def delete_custom_category(
    room_id: str,
    category_id: int,
    player_id: str,  # Query param: who is deleting
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom category from a room

    Only the host can delete custom categories.
    """
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
    db.delete(category)
    await db.commit()

    # Broadcast to all players in room
    await room.broadcast(
        {"type": "custom_category_removed", "category_id": category_id, "category_name": category.name}
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
    player_id: str | None = None

    try:
        # Send initial room state
        await websocket.send_text(
            json.dumps(
                {
                    "type": "room_state",
                    "players": room.get_player_list(),
                    "categories": room.metadata.categories,
                    "gamePhase": room.metadata.game_phase,
                    "roundStartTime": room.metadata.round_start_time,
                    "roundLength": room.metadata.round_length,
                    "difficulty": room.metadata.difficulty,
                    "maxRounds": room.metadata.max_rounds,
                    "padVisibility": room.metadata.pad_visibility,
                    "language": room.metadata.language,
                }
            )
        )

        # Handle messages
        while True:
            data = await websocket.receive_text()
            message = await parse_message(data, room, websocket)

            if message:
                # Track player_id from join message
                if message.get("type") == "join":
                    player_id = message.get("playerId")

    except WebSocketDisconnect:
        logger.info("[WebSocket] Client disconnected from room %s", room_id)
    except Exception:
        logger.exception("[WebSocket] Error in room %s", room_id)
    finally:
        # Clean up player
        if player_id and room:
            await room.remove_player(player_id)
            await room.broadcast({"type": "player_left", "playerId": player_id})
            await room.persist()

        # Periodic cleanup loop handles hibernation and removal with correct timeouts


async def parse_message(data: str, room, websocket: WebSocket):
    """Parse and handle incoming WebSocket messages."""
    try:
        message = json.loads(data)
        msg_type = message.get("type")

        # Find player_id from websocket connection
        sender_player_id = None
        for pid, player in room.players.items():
            if player.websocket == websocket:
                sender_player_id = pid
                break

        # Update last activity (except for join messages, handled separately)
        if msg_type != "join" and sender_player_id:
            room.update_player_activity(sender_player_id)

        # Handle different message types
        if msg_type == "join":
            player_id = message.get("playerId")
            name = message.get("name")

            try:
                player, is_reconnecting_host = await room.add_player(player_id, name, websocket)

                # Broadcast updated player list to everyone
                all_players = room.get_player_list()
                logger.info("[Server] Broadcasting player_joined with players: %s", all_players)

                await room.broadcast(
                    {
                        "type": "player_joined",
                        "playerId": player_id,
                        "name": name,
                        "players": all_players,
                        "isHost": player_id == room.host_id,
                    }
                )

                # If host reconnected, notify them
                if is_reconnecting_host:
                    await websocket.send_text(json.dumps({"type": "host_restored", "message": "You are still the host"}))

                await room.persist()
                return message

            except ValueError as e:
                # Room is full
                logger.warning("[Server] Player %s (%s) cannot join: %s", name, player_id, e)
                await websocket.send_text(json.dumps({"type": "join_error", "error": "room_full", "message": str(e)}))
                await websocket.close(code=1008, reason=str(e))
                return None

        if msg_type == "start_game":
            logger.info("[Server] Raw start_game message: %s", json.dumps(message))

            player_count = len(room.players)
            if player_count < 2:
                logger.warning("[Server] Cannot start game: Not enough players. Current player count: %s", player_count)
                return None

            # Prevent duplicate processing
            if room.metadata.game_phase != "lobby":
                logger.info("[Server] Ignoring start_game message - game already started.")
                return None

            # Store game settings
            room.metadata.round_length = message.get("roundLength")
            room.metadata.difficulty = message.get("difficulty")
            room.metadata.max_rounds = message.get("rounds") or 5
            room.metadata.game_phase = "drawing"
            room.metadata.current_round = 0

            # Initialise per-player scores for this game
            room.metadata.player_scores = dict.fromkeys(room.players, 0)

            # Clear ready players when game starts
            room.metadata.ready_players.clear()

            logger.info("[Server] Game configured with round length: %s seconds", message.get("roundLength"))

            await room.broadcast(message)
            await room.persist()
            return message

        if msg_type == "start_round":
            round_start_time = int(time.time() * 1000)
            room.metadata.round_start_time = round_start_time
            room.metadata.game_phase = "drawing"
            room.metadata.current_round = message.get("round", room.metadata.current_round + 1)

            # Store cards for server-side scoring
            room.metadata.player_cards = message.get("cards", {})
            room.metadata.guess_submissions = []
            room.metadata.submitted_players = set()
            room.metadata.player_count_for_scoring = len(room.players)

            # Ensure any new players joining mid-game have a score entry
            for pid in room.players:
                if pid not in room.metadata.player_scores:
                    room.metadata.player_scores[pid] = 0

            # Cancel any stale scoring task from a previous round
            if room._round_scoring_task:
                room._round_scoring_task.cancel()
                room._round_scoring_task = None

            # Clear ready players when starting a new round
            room.metadata.ready_players.clear()

            logger.info("[Server] Starting round %s at %s", room.metadata.current_round, round_start_time)

            # Broadcast with server-generated roundStartTime
            await room.broadcast({**message, "roundStartTime": round_start_time})
            await room.persist()
            return message

        if msg_type == "round_complete":
            # Server now generates round_complete via score_and_broadcast_round()
            logger.info("[Server] Ignoring client-sent round_complete — server handles scoring")
            return message

        if msg_type == "game_complete":
            # Server now generates game_complete via _broadcast_game_complete_after_delay()
            logger.info("[Server] Ignoring client-sent game_complete — server handles end-game")
            return message

        if msg_type == "player_ready":
            player_id = message.get("playerId")
            room.metadata.ready_players.add(player_id)
            logger.info("[Server] Player %s is ready. Ready count: %s/%s", player_id, len(room.metadata.ready_players), len(room.players))

            # Broadcast ready status to all players
            await room.broadcast({"type": "ready_status", "readyCount": len(room.metadata.ready_players), "totalPlayers": len(room.players)})
            await room.persist()
            return message

        if msg_type == "start_guessing":
            room.metadata.game_phase = "guessing"
            room.metadata.player_count_for_scoring = len(room.players)

            # Start fallback scoring timeout using configured round length (default 30s)
            guessing_timeout = room.metadata.round_length or 30
            room.start_scoring_timeout(guessing_timeout)

            await room.broadcast(message)
            await room.persist()
            return message

        if msg_type == "submit_guess":
            player_id = message.get("playerId")
            target_player_id = message.get("targetPlayerId")
            guesses = message.get("guesses", [])

            if player_id and target_player_id:
                room.metadata.guess_submissions.append(
                    {"playerId": player_id, "targetPlayerId": target_player_id, "guesses": guesses}
                )
                room.metadata.submitted_players.add(player_id)

                submitted = len(room.metadata.submitted_players)
                expected = room.metadata.player_count_for_scoring
                logger.info("[Server] Guess submitted by %s: %s/%s players submitted", player_id, submitted, expected)

                if expected > 0 and submitted >= expected:
                    await room.score_and_broadcast_round()

            return message

        if msg_type == "restart_game":
            logger.info("[Server] Host initiated game restart")

            # Cancel any pending scoring task
            if room._round_scoring_task:
                room._round_scoring_task.cancel()
                room._round_scoring_task = None

            # Reset scoring state for new game
            room.metadata.player_scores = {}
            room.metadata.current_round = 0
            room.metadata.guess_submissions = []
            room.metadata.submitted_players = set()
            room.metadata.player_cards = {}

            # Reset ready players and phase
            room.metadata.ready_players.clear()
            room.metadata.game_phase = "lobby"
            await room.broadcast(message)
            await room.persist()
            return message

        if msg_type == "heartbeat":
            # Activity already updated above, no need to broadcast
            return message

        if msg_type == "settings_update":
            # Only allow the current host to broadcast settings updates
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                # Persist the settings in room metadata
                room.metadata.difficulty = message.get("difficulty")
                room.metadata.max_rounds = message.get("rounds")
                room.metadata.round_length = message.get("roundLength")

                logger.info("[Server] Broadcasting settings update from host: %s", message)
                await room.broadcast(message)
                await room.persist()
            else:
                logger.info("[Server] Ignored settings_update from non-host connection")

            return message

        if msg_type == "language_update":
            # Only allow the current host to change language
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                new_language = message.get("language", "en")
                room.metadata.language = new_language
                logger.info("[Server] Host updated room language to %s", new_language)
                await room.broadcast({"type": "language_update", "language": new_language})
                await room.persist()
            else:
                logger.info("[Server] Ignored language_update from non-host connection")

            return message

        if msg_type == "draw_stroke" or msg_type == "draw_stroke_partial":
            # Relay stroke data to all clients (including sender)
            await room.broadcast(message)
            return message

        if msg_type == "drawpad_clear":
            # Only allow host to clear the shared waiting-room pad
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                logger.info("[Server] Host cleared drawpad")
                await room.broadcast(message)
            else:
                logger.info("[Server] Ignored drawpad_clear from non-host connection")

            return message

        if msg_type == "pad_visibility":
            # Only allow host to change visibility
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                room.metadata.pad_visibility = message.get("visible", True)
                logger.info("[Server] Host updated pad visibility to %s", message.get("visible"))
                await room.broadcast(message)
                await room.persist()
            else:
                logger.info("[Server] Ignored pad_visibility from non-host connection")

            return message

        if msg_type == "privacy_changed":
            # Only allow host to change room privacy
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                room.metadata.is_private = message.get("isPrivate", False)
                logger.info("[Server] Host updated room privacy to %s", message.get("isPrivate"))
                # Don't broadcast privacy changes - it's a backend-only setting
                await room.persist()
            else:
                logger.info("[Server] Ignored privacy_changed from non-host connection")

            return message

        if msg_type == "initiate_kick":
            # Initiate a vote to kick a player
            if sender_player_id:
                target_player_id = message.get("targetPlayerId")
                if target_player_id:
                    result = await room.initiate_kick_vote(sender_player_id, target_player_id)
                    if not result.get("success"):
                        # Send error to initiator
                        await websocket.send_text(json.dumps({"type": "kick_error", "error": result.get("error", "Failed to initiate kick vote")}))
                else:
                    logger.warning("[Server] Missing targetPlayerId in initiate_kick message")

            return message

        if msg_type == "cast_kick_vote":
            # Cast a vote to kick a player
            if sender_player_id:
                target_player_id = message.get("targetPlayerId")
                if target_player_id:
                    result = await room.cast_kick_vote(sender_player_id, target_player_id)
                    if not result.get("success"):
                        # Send error to voter
                        await websocket.send_text(json.dumps({"type": "kick_error", "error": result.get("error", "Failed to cast vote")}))
                else:
                    logger.warning("[Server] Missing targetPlayerId in cast_kick_vote message")

            return message

        if msg_type == "request_game_state":
            # Send current game state to the requester
            players_with_categories = [{"id": p.id, "name": p.name, "categories": p.categories} for p in room.players.values()]

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "room_state",
                        "players": players_with_categories,
                        "categories": room.metadata.categories,
                        "gamePhase": room.metadata.game_phase,
                        "roundStartTime": room.metadata.round_start_time,
                        "roundLength": room.metadata.round_length,
                        "language": room.metadata.language,
                    }
                )
            )

            return message

        # Default: relay to all clients including sender
        await room.broadcast(message)
        return message

    except Exception:
        logger.exception("[Server] Error processing message")
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
