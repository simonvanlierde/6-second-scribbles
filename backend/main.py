"""
FastAPI Server for Six Second Scribbles

Architecture: "Dumb Pipe" Pattern
- Server only relays messages between clients
- All game logic lives in client-side GameEngine
- Migrated from PartyKit for better scalability
"""
import json
import time
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from game_room import room_manager


app = FastAPI(title="Six Second Scribbles API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Six Second Scribbles API"}


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

            await room.add_player(player_id, name, websocket)

            # Broadcast updated player list to everyone
            all_players = room.get_player_list()
            print(f"[Server] Broadcasting player_joined with players: {all_players}")

            await room.broadcast({
                "type": "player_joined",
                "playerId": player_id,
                "name": name,
                "players": all_players,
            })

            return message

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
