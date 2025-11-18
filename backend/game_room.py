"""
Game Room Manager for Six Second Scribbles

Architecture: "Dumb Pipe" Pattern
- Server only relays messages between clients
- All game logic lives in client-side GameEngine
- Easy migration from PartyKit
"""
import asyncio
import json
import time
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
from dataclasses import dataclass, field


@dataclass
class PlayerInfo:
    id: str
    name: str
    websocket: WebSocket
    categories: List[str] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)


@dataclass
class RoomMetadata:
    categories: List[str] = field(default_factory=list)
    game_phase: str = "lobby"
    round_start_time: Optional[int] = None
    round_length: Optional[int] = None
    difficulty: str = "medium"
    max_rounds: int = 5
    pad_visibility: bool = True
    ready_players: Set[str] = field(default_factory=set)
    is_private: bool = False  # Private rooms don't appear in random join


class GameRoom:
    """Manages a single game room with multiple players"""

    # Idle timeout configuration (3 minutes of inactivity during game)
    IDLE_TIMEOUT_MS = 3 * 60 * 1000

    # Host transfer delay (1 second to allow for reconnections)
    HOST_TRANSFER_DELAY_MS = 1000

    # Maximum players per room
    MAX_PLAYERS = 10

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, PlayerInfo] = {}
        self.host_id: Optional[str] = None
        self.metadata = RoomMetadata()
        self._idle_check_task: Optional[asyncio.Task] = None
        self._pending_host_transfer: Optional[asyncio.Task] = None
        self._last_host_id: Optional[str] = None  # Track last host for reconnection

    async def start_idle_check(self):
        """Start periodic idle player check"""
        self._idle_check_task = asyncio.create_task(self._idle_check_loop())

    async def stop_idle_check(self):
        """Stop idle player check"""
        if self._idle_check_task:
            self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass

    async def _idle_check_loop(self):
        """Periodically check for idle players"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                await self._check_idle_players()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[GameRoom {self.room_id}] Error in idle check: {e}")

    async def _check_idle_players(self):
        """Check for and disconnect idle players during active game phases"""
        if self.metadata.game_phase not in ['lobby', 'complete']:
            now = time.time() * 1000  # Convert to milliseconds
            idle_players = []

            for player_id, player in self.players.items():
                idle_time = now - (player.last_activity * 1000)
                if idle_time > self.IDLE_TIMEOUT_MS:
                    print(f"[GameRoom {self.room_id}] Player {player.name} ({player_id}) is idle for {idle_time/1000}s")
                    idle_players.append(player_id)

            # Disconnect idle players
            for player_id in idle_players:
                player = self.players.get(player_id)
                if player:
                    print(f"[GameRoom {self.room_id}] Disconnecting idle player: {player.name}")
                    try:
                        await player.websocket.close(code=1000, reason="Disconnected due to inactivity")
                    except:
                        pass

    async def add_player(self, player_id: str, name: str, websocket: WebSocket):
        """
        Add a player to the room

        Returns tuple: (player, is_reconnecting_host)
        Raises ValueError if room is full
        """
        # Check if room is at capacity (but allow existing player to reconnect)
        if player_id not in self.players and len(self.players) >= self.MAX_PLAYERS:
            raise ValueError(f"Room is full (maximum {self.MAX_PLAYERS} players)")

        # Check if this is the previous host reconnecting
        is_reconnecting_host = (player_id == self._last_host_id and player_id not in self.players)

        categories = self._generate_categories_for_player()
        player = PlayerInfo(
            id=player_id,
            name=name,
            websocket=websocket,
            categories=categories,
            last_activity=time.time()
        )
        self.players[player_id] = player

        # Cancel pending host transfer if the host reconnected
        if is_reconnecting_host and self._pending_host_transfer:
            self._pending_host_transfer.cancel()
            self._pending_host_transfer = None
            self.host_id = player_id
            print(f"[GameRoom {self.room_id}] Host {name} ({player_id}) reconnected, host transfer cancelled")

        # If this is the first player, make them host
        elif len(self.players) == 1:
            self.host_id = player_id
            self._last_host_id = player_id

        return player, is_reconnecting_host

    async def remove_player(self, player_id: str):
        """Remove a player from the room"""
        if player_id in self.players:
            del self.players[player_id]

        # Handle host transfer if the host left
        if player_id == self.host_id:
            if len(self.players) > 0:
                # Schedule delayed host transfer to allow for reconnection
                print(f"[GameRoom {self.room_id}] Host disconnected, scheduling transfer in {self.HOST_TRANSFER_DELAY_MS}ms...")

                # Cancel any existing pending transfer
                if self._pending_host_transfer:
                    self._pending_host_transfer.cancel()

                # Schedule new transfer
                self._pending_host_transfer = asyncio.create_task(
                    self._delayed_host_transfer(player_id)
                )
            else:
                # No players left, room is effectively closed
                self.host_id = None
                self._last_host_id = None
                print(f"[GameRoom {self.room_id}] Room is now empty")

    async def _delayed_host_transfer(self, old_host_id: str):
        """Transfer host after a delay, allowing for reconnection"""
        try:
            # Wait for the delay
            await asyncio.sleep(self.HOST_TRANSFER_DELAY_MS / 1000)

            # Check if host reconnected during the delay
            if old_host_id in self.players:
                print(f"[GameRoom {self.room_id}] Host reconnected, cancelling transfer")
                self.host_id = old_host_id
                return

            # Transfer host if there are still players
            if len(self.players) > 0:
                new_host = list(self.players.values())[0]
                self.host_id = new_host.id
                self._last_host_id = new_host.id

                # Notify all remaining players of the new host
                await self.broadcast({
                    "type": "host_changed",
                    "newHostId": new_host.id
                })

                print(f"[GameRoom {self.room_id}] Host transferred to {new_host.name} ({new_host.id})")
            else:
                self.host_id = None
                self._last_host_id = None

        except asyncio.CancelledError:
            print(f"[GameRoom {self.room_id}] Host transfer cancelled (host reconnected)")
        finally:
            self._pending_host_transfer = None

    def update_player_activity(self, player_id: str):
        """Update the last activity timestamp for a player"""
        if player_id in self.players:
            self.players[player_id].last_activity = time.time()

    async def broadcast(self, message: dict, exclude: Optional[str] = None):
        """Broadcast a message to all players in the room"""
        message_str = json.dumps(message)
        disconnected_players = []

        for player_id, player in self.players.items():
            if exclude and player_id == exclude:
                continue

            try:
                await player.websocket.send_text(message_str)
            except Exception as e:
                print(f"[GameRoom {self.room_id}] Error sending to {player.name}: {e}")
                disconnected_players.append(player_id)

        # Clean up disconnected players
        for player_id in disconnected_players:
            await self.remove_player(player_id)
            await self.broadcast({
                "type": "player_left",
                "playerId": player_id
            })

    async def send_to_player(self, player_id: str, message: dict):
        """Send a message to a specific player"""
        if player_id in self.players:
            player = self.players[player_id]
            try:
                await player.websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"[GameRoom {self.room_id}] Error sending to {player.name}: {e}")
                await self.remove_player(player_id)

    def get_player_list(self) -> List[Dict[str, str]]:
        """Get the list of all players in the room"""
        return [{"id": p.id, "name": p.name} for p in self.players.values()]

    def _generate_categories_for_player(self) -> List[str]:
        """Generate categories for a player (placeholder)"""
        # Replace with actual category generation logic
        return ["Category1", "Category2", "Category3"]

    def is_empty(self) -> bool:
        """Check if the room is empty"""
        return len(self.players) == 0

    async def cleanup_custom_categories(self):
        """Delete all custom categories created for this room"""
        try:
            from database import async_session_maker
            from db_models import Category
            from sqlalchemy import delete

            async with async_session_maker() as session:
                # Delete all categories with this room_id
                stmt = delete(Category).where(Category.room_id == self.room_id)
                result = await session.execute(stmt)
                await session.commit()

                deleted_count = result.rowcount
                if deleted_count > 0:
                    print(f"[GameRoom {self.room_id}] Cleaned up {deleted_count} custom categories")
        except Exception as e:
            print(f"[GameRoom {self.room_id}] Error cleaning up custom categories: {e}")


class RoomManager:
    """Manages all game rooms"""

    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def get_or_create_room(self, room_id: str) -> GameRoom:
        """Get an existing room or create a new one"""
        if room_id not in self.rooms:
            room = GameRoom(room_id)
            self.rooms[room_id] = room
            asyncio.create_task(room.start_idle_check())
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        """Get an existing room"""
        return self.rooms.get(room_id)

    async def remove_room(self, room_id: str):
        """Remove a room and clean up custom categories"""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            await room.stop_idle_check()
            await room.cleanup_custom_categories()  # Clean up custom categories
            del self.rooms[room_id]
            print(f"[RoomManager] Removed room {room_id}")

    async def cleanup_empty_rooms(self):
        """Remove empty rooms"""
        empty_rooms = [
            room_id for room_id, room in self.rooms.items()
            if room.is_empty()
        ]

        for room_id in empty_rooms:
            await self.remove_room(room_id)

    def find_random_public_room(self, max_players: int = 10) -> Optional[str]:
        """
        Find a random public room that's available to join

        Criteria:
        - Not private (is_private = False)
        - Not full (< max_players)
        - In lobby phase (not mid-game)
        - Has at least 1 player (not empty)

        Returns room_id if found, None otherwise
        """
        import random

        available_rooms = []

        for room_id, room in self.rooms.items():
            # Check if room meets criteria
            if (not room.metadata.is_private and
                len(room.players) < max_players and
                len(room.players) > 0 and
                room.metadata.game_phase == "lobby"):
                available_rooms.append(room_id)

        if available_rooms:
            return random.choice(available_rooms)

        return None


# Global room manager instance
room_manager = RoomManager()
