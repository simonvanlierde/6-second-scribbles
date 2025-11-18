"""
FastAPI Server for Six Second Scribbles

Architecture: "Dumb Pipe" Pattern
- Server only relays messages between clients
- All game logic lives in client-side GameEngine
- Migrated from PartyKit for better scalability
"""
import json
import time
import random
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from game_room import room_manager
from database import get_db, init_db, close_db
from db_models import Category, Card
from scoring import guess_matcher


app = FastAPI(
    title="Six Second Scribbles API",
    description="Real-time multiplayer drawing game backend",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class GuessRequest(BaseModel):
    guesses: List[str]
    correct_answers: List[str]
    alternatives: dict = {}


class GuessResponse(BaseModel):
    score: int
    total: int
    percentage: float
    matches: List[dict]
    unmatched_answers: List[str]


class CustomCategoryCreate(BaseModel):
    name: str
    items: List[str]  # List of items for this category
    difficulty: str = "medium"
    description: Optional[str] = None
    created_by: str  # Player ID


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Six Second Scribbles API...")
    await init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("👋 Shutting down...")
    await close_db()
    print("✅ Database connections closed")


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Six Second Scribbles API",
        "version": "2.0.0"
    }


@app.get("/api/rooms/random")
async def get_random_room():
    """
    Find a random public room that's available to join

    Returns:
    - room_code: The room code to join
    - player_count: Current number of players in the room

    Returns 404 if no available rooms found
    """
    room_code = room_manager.find_random_public_room(max_players=10)

    if not room_code:
        raise HTTPException(
            status_code=404,
            detail="No available public rooms found. Try creating a new room!"
        )

    room = room_manager.get_room(room_code)
    player_count = len(room.players) if room else 0

    return {
        "room_code": room_code,
        "player_count": player_count,
        "max_players": 10
    }


@app.get("/api/categories")
async def get_categories(
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories, optionally filtered by difficulty

    Query params:
        difficulty: Filter by difficulty (easy, medium, hard)
    """
    query = select(Category)

    if difficulty:
        query = query.where(Category.difficulty == difficulty.lower())

    result = await db.execute(query)
    categories = result.scalars().all()

    return {
        "categories": [cat.to_dict() for cat in categories],
        "count": len(categories)
    }


@app.get("/api/categories/{category_id}")
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific category with its items"""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get cards for this category
    cards_result = await db.execute(
        select(Card).where(Card.category_id == category_id)
    )
    cards = cards_result.scalars().all()

    return {
        "category": category.to_dict(),
        "items": [card.item for card in cards],
        "cards": [card.to_dict() for card in cards]
    }


@app.get("/api/cards/random")
async def get_random_cards(
    difficulty: str = "medium",
    count: int = 1,
    player_count: int = 2,
    room_id: Optional[str] = None,  # Include room-specific categories
    db: AsyncSession = Depends(get_db)
):
    """
    Get random cards for a game

    Query params:
        difficulty: Difficulty level (easy, medium, hard)
        count: Number of rounds (cards per player)
        player_count: Number of players
        room_id: If provided, includes custom categories for this room

    Returns unique categories for each player for each round
    """
    # Build query for global categories with this difficulty
    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.room_id.is_(None)  # Global categories only
    )
    result = await db.execute(query)
    categories = list(result.scalars().all())

    # If room_id provided, also include custom categories for that room
    if room_id:
        custom_query = select(Category).where(
            Category.room_id == room_id
        )
        custom_result = await db.execute(custom_query)
        custom_categories = list(custom_result.scalars().all())
        categories.extend(custom_categories)

    if not categories:
        raise HTTPException(
            status_code=404,
            detail=f"No categories found for difficulty: {difficulty}"
        )

    total_needed = count * player_count

    if len(categories) < total_needed:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough categories ({len(categories)}) for {player_count} players and {count} rounds. "
                   f"Available: {len(categories)}, needed: {total_needed}"
        )

    # Randomly select categories without replacement
    selected_categories = random.sample(categories, total_needed)

    # Get cards for selected categories
    cards_by_category = {}
    for category in selected_categories:
        cards_result = await db.execute(
            select(Card).where(Card.category_id == category.id)
        )
        cards = cards_result.scalars().all()
        cards_by_category[category.id] = {
            "category": category.name,
            "items": [card.item for card in cards],
            "alternatives": {card.item: card.alternatives for card in cards},
            "is_custom": category.room_id is not None
        }

    return {
        "difficulty": difficulty,
        "categories": cards_by_category,
        "includes_custom": room_id is not None
    }


@app.post("/api/score/guesses", response_model=GuessResponse)
async def score_guesses(request: GuessRequest):
    """
    Score player guesses using fuzzy matching

    Body:
        guesses: List of player's guesses
        correct_answers: List of correct answers
        alternatives: Dict mapping answers to alternative spellings
    """
    result = guess_matcher.score_guesses(
        guesses=request.guesses,
        correct_answers=request.correct_answers,
        alternatives_map=request.alternatives
    )

    return GuessResponse(**result)


# Custom Categories (Room-specific)
@app.post("/api/rooms/{room_id}/categories")
async def create_custom_category(
    room_id: str,
    category_data: CustomCategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a custom category for a specific room

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
        raise HTTPException(
            status_code=400,
            detail="Custom category must have at least 5 items"
        )

    # Create category
    category = Category(
        name=category_data.name,
        difficulty=category_data.difficulty,
        description=category_data.description or f"Custom category for room {room_id}",
        room_id=room_id,
        created_by=category_data.created_by
    )
    db.add(category)
    await db.flush()  # Get the category ID

    # Create cards for this category
    for item in category_data.items:
        card = Card(
            category_id=category.id,
            item=item.strip(),
            alternatives=[]
        )
        db.add(card)

    await db.commit()

    # Broadcast to all players in room
    await room.broadcast({
        "type": "custom_category_added",
        "category": category.to_dict(),
        "items": category_data.items
    })

    return {
        "success": True,
        "category": category.to_dict(),
        "message": f"Custom category '{category_data.name}' created with {len(category_data.items)} items"
    }


@app.get("/api/rooms/{room_id}/categories")
async def get_room_categories(
    room_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all custom categories for a specific room

    Returns only the categories created for this room, not global categories.
    """
    result = await db.execute(
        select(Category).where(Category.room_id == room_id)
    )
    categories = result.scalars().all()

    # Get cards for each category
    categories_with_items = []
    for category in categories:
        cards_result = await db.execute(
            select(Card).where(Card.category_id == category.id)
        )
        cards = cards_result.scalars().all()

        categories_with_items.append({
            **category.to_dict(),
            "items": [card.item for card in cards]
        })

    return {
        "room_id": room_id,
        "categories": categories_with_items,
        "count": len(categories_with_items)
    }


@app.delete("/api/rooms/{room_id}/categories/{category_id}")
async def delete_custom_category(
    room_id: str,
    category_id: int,
    player_id: str,  # Query param: who is deleting
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a custom category from a room

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
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.room_id == room_id
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Custom category not found")

    # Delete category (cards will cascade delete)
    await db.delete(category)
    await db.commit()

    # Broadcast to all players in room
    await room.broadcast({
        "type": "custom_category_removed",
        "category_id": category_id,
        "category_name": category.name
    })

    return {
        "success": True,
        "message": f"Custom category '{category.name}' deleted"
    }


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
    print(f"[WebSocket] Connection accepted for room {room_id}")

    room = room_manager.get_or_create_room(room_id)
    player_id: Optional[str] = None

    try:
        # Send initial room state
        await websocket.send_text(json.dumps({
            "type": "room_state",
            "players": room.get_player_list(),
            "categories": room.metadata.categories,
            "gamePhase": room.metadata.game_phase,
            "roundStartTime": room.metadata.round_start_time,
            "roundLength": room.metadata.round_length,
            "difficulty": room.metadata.difficulty,
            "maxRounds": room.metadata.max_rounds,
            "padVisibility": room.metadata.pad_visibility,
        }))

        # Handle messages
        while True:
            data = await websocket.receive_text()
            message = json.parse_message(data, room, websocket)

            if message:
                # Track player_id from join message
                if message.get("type") == "join":
                    player_id = message.get("playerId")

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from room {room_id}")
    except Exception as e:
        print(f"[WebSocket] Error in room {room_id}: {e}")
    finally:
        # Clean up player
        if player_id and room:
            await room.remove_player(player_id)
            await room.broadcast({
                "type": "player_left",
                "playerId": player_id
            })

        # Clean up empty rooms
        await room_manager.cleanup_empty_rooms()


async def parse_message(data: str, room, websocket: WebSocket):
    """Parse and handle incoming WebSocket messages"""
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
                print(f"[Server] Broadcasting player_joined with players: {all_players}")

                await room.broadcast({
                    "type": "player_joined",
                    "playerId": player_id,
                    "name": name,
                    "players": all_players,
                    "isHost": player_id == room.host_id,
                })

                # If host reconnected, notify them
                if is_reconnecting_host:
                    await websocket.send_text(json.dumps({
                        "type": "host_restored",
                        "message": "You are still the host"
                    }))

                return message

            except ValueError as e:
                # Room is full
                print(f"[Server] Player {name} ({player_id}) cannot join: {e}")
                await websocket.send_text(json.dumps({
                    "type": "join_error",
                    "error": "room_full",
                    "message": str(e)
                }))
                await websocket.close(code=1008, reason=str(e))
                return None

        elif msg_type == "start_game":
            print(f"[Server] Raw start_game message: {json.dumps(message)}")

            player_count = len(room.players)
            if player_count < 2:
                print(f"[Server] Cannot start game: Not enough players. Current player count: {player_count}")
                return None

            # Prevent duplicate processing
            if room.metadata.game_phase != "lobby":
                print("[Server] Ignoring start_game message - game already started.")
                return None

            # Store game settings
            room.metadata.round_length = message.get("roundLength")
            room.metadata.difficulty = message.get("difficulty")
            room.metadata.max_rounds = message.get("rounds")
            room.metadata.game_phase = "drawing"

            # Clear ready players when game starts
            room.metadata.ready_players.clear()

            print(f"[Server] Game configured with round length: {message.get('roundLength')} seconds")

            # Broadcast to all clients
            await room.broadcast(message)

        elif msg_type == "start_round":
            round_start_time = int(time.time() * 1000)
            room.metadata.round_start_time = round_start_time
            room.metadata.game_phase = "drawing"

            # Clear ready players when starting a new round
            room.metadata.ready_players.clear()

            print(f"[Server] Starting round {message.get('round')} at {round_start_time}")

            # Broadcast with server-generated roundStartTime
            await room.broadcast({
                **message,
                "roundStartTime": round_start_time,
            })

        elif msg_type == "round_complete":
            room.metadata.game_phase = "scoring"
            await room.broadcast(message)

        elif msg_type == "game_complete":
            room.metadata.game_phase = "complete"
            room.metadata.ready_players.clear()
            await room.broadcast(message)

        elif msg_type == "player_ready":
            player_id = message.get("playerId")
            room.metadata.ready_players.add(player_id)
            print(f"[Server] Player {player_id} is ready. Ready count: {len(room.metadata.ready_players)}/{len(room.players)}")

            # Broadcast ready status to all players
            await room.broadcast({
                "type": "ready_status",
                "readyCount": len(room.metadata.ready_players),
                "totalPlayers": len(room.players),
            })

        elif msg_type == "restart_game":
            print("[Server] Host initiated game restart")

            # Reset ready players
            room.metadata.ready_players.clear()

            # Reset game phase to lobby
            room.metadata.game_phase = "lobby"

            # Broadcast restart to all players
            await room.broadcast(message)

        elif msg_type == "heartbeat":
            # Activity already updated above, no need to broadcast
            pass

        elif msg_type == "settings_update":
            # Only allow the current host to broadcast settings updates
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                # Persist the settings in room metadata
                room.metadata.difficulty = message.get("difficulty")
                room.metadata.max_rounds = message.get("rounds")
                room.metadata.round_length = message.get("roundLength")

                print(f"[Server] Broadcasting settings update from host: {message}")
                await room.broadcast(message)
            else:
                print(f"[Server] Ignored settings_update from non-host connection")

        elif msg_type == "draw_stroke":
            # Relay stroke data to all clients (including sender)
            await room.broadcast(message)

        elif msg_type == "draw_stroke_partial":
            # Relay incremental stroke points to all clients
            await room.broadcast(message)

        elif msg_type == "drawpad_clear":
            # Only allow host to clear the shared waiting-room pad
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                print("[Server] Host cleared drawpad")
                await room.broadcast(message)
            else:
                print("[Server] Ignored drawpad_clear from non-host connection")

        elif msg_type == "pad_visibility":
            # Only allow host to change visibility
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                room.metadata.pad_visibility = message.get("visible", True)
                print(f"[Server] Host updated pad visibility to {message.get('visible')}")
                await room.broadcast(message)
            else:
                print("[Server] Ignored pad_visibility from non-host connection")

        elif msg_type == "privacy_changed":
            # Only allow host to change room privacy
            if sender_player_id and room.host_id and sender_player_id == room.host_id:
                room.metadata.is_private = message.get("isPrivate", False)
                print(f"[Server] Host updated room privacy to {message.get('isPrivate')}")
                # Don't broadcast privacy changes - it's a backend-only setting
            else:
                print("[Server] Ignored privacy_changed from non-host connection")

        elif msg_type == "request_game_state":
            # Send current game state to the requester
            players_with_categories = [
                {
                    "id": p.id,
                    "name": p.name,
                    "categories": p.categories
                }
                for p in room.players.values()
            ]

            await websocket.send_text(json.dumps({
                "type": "room_state",
                "players": players_with_categories,
                "categories": room.metadata.categories,
                "gamePhase": room.metadata.game_phase,
                "roundStartTime": room.metadata.round_start_time,
                "roundLength": room.metadata.round_length,
            }))

        else:
            # For all other messages, just relay to all clients including sender
            await room.broadcast(message)

        return message

    except Exception as e:
        print(f"[Server] Error processing message: {e}")
        return None


json.parse_message = parse_message


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
