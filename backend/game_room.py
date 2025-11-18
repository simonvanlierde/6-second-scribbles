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
class KickVote:
    """Tracks votes to kick a player"""
    target_player_id: str
    target_player_name: str
    initiated_by: str
    voters: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 60)  # 1 minute


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

    # Room hibernation timeout (5 minutes of being empty)
    HIBERNATION_TIMEOUT_SECONDS = 5 * 60

    # Kick vote timeout (1 minute)
    KICK_VOTE_TIMEOUT_SECONDS = 60

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, PlayerInfo] = {}
        self.host_id: Optional[str] = None
        self.metadata = RoomMetadata()
        self._idle_check_task: Optional[asyncio.Task] = None
        self._pending_host_transfer: Optional[asyncio.Task] = None
        self._last_host_id: Optional[str] = None  # Track last host for reconnection
        self._created_at = time.time()
        self._last_activity = time.time()
        self._emptied_at: Optional[float] = None  # When room became empty
        self.is_hibernated = False
        self.active_kick_votes: Dict[str, KickVote] = {}  # target_player_id -> KickVote

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
        """Periodically check for idle players and cleanup expired votes"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                await self._check_idle_players()
                self.cleanup_expired_votes()
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

        # Room is no longer empty - wake from hibernation if needed
        if self.is_hibernated:
            print(f"[GameRoom {self.room_id}] Waking from hibernation")
            self.is_hibernated = False

        self._last_activity = time.time()
        self._emptied_at = None

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

        # Mark when room becomes empty
        if len(self.players) == 0:
            self._emptied_at = time.time()
            print(f"[GameRoom {self.room_id}] Room is now empty, marked for hibernation/cleanup")

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

    async def initiate_kick_vote(self, initiator_id: str, target_player_id: str) -> Dict:
        """
        Initiate a vote to kick a player

        Returns dict with status and info about the vote
        """
        # Validate players exist
        if initiator_id not in self.players:
            return {"success": False, "error": "Initiator not in room"}

        if target_player_id not in self.players:
            return {"success": False, "error": "Target player not in room"}

        # Can't kick yourself
        if initiator_id == target_player_id:
            return {"success": False, "error": "Cannot kick yourself"}

        # Check if vote already exists
        if target_player_id in self.active_kick_votes:
            vote = self.active_kick_votes[target_player_id]
            if time.time() < vote.expires_at:
                return {"success": False, "error": "Vote already in progress"}
            else:
                # Clean up expired vote
                del self.active_kick_votes[target_player_id]

        # Host can kick directly
        is_host_kicking = (initiator_id == self.host_id)
        target_is_host = (target_player_id == self.host_id)

        if is_host_kicking and not target_is_host:
            # Host kicks non-host player directly
            await self.kick_player(target_player_id, "Kicked by host")
            return {
                "success": True,
                "immediate": True,
                "reason": "Host kicked player"
            }

        # Create vote
        target_player = self.players[target_player_id]
        vote = KickVote(
            target_player_id=target_player_id,
            target_player_name=target_player.name,
            initiated_by=initiator_id,
            voters={initiator_id}  # Initiator automatically votes yes
        )
        self.active_kick_votes[target_player_id] = vote

        # Broadcast vote started
        await self.broadcast({
            "type": "kick_vote_started",
            "targetPlayerId": target_player_id,
            "targetPlayerName": target_player.name,
            "initiatedBy": initiator_id,
            "requiredVotes": self._get_required_votes(target_is_host),
            "currentVotes": 1,
            "expiresAt": vote.expires_at * 1000  # Convert to ms for frontend
        })

        print(f"[GameRoom {self.room_id}] Kick vote started for {target_player.name} by {self.players[initiator_id].name}")

        return {
            "success": True,
            "immediate": False,
            "vote_id": target_player_id
        }

    async def cast_kick_vote(self, voter_id: str, target_player_id: str) -> Dict:
        """Cast a vote to kick a player"""
        # Validate voter exists
        if voter_id not in self.players:
            return {"success": False, "error": "Voter not in room"}

        # Check if vote exists
        if target_player_id not in self.active_kick_votes:
            return {"success": False, "error": "No active vote for this player"}

        vote = self.active_kick_votes[target_player_id]

        # Check if vote expired
        if time.time() > vote.expires_at:
            del self.active_kick_votes[target_player_id]
            await self.broadcast({
                "type": "kick_vote_expired",
                "targetPlayerId": target_player_id
            })
            return {"success": False, "error": "Vote has expired"}

        # Can't vote to kick yourself
        if voter_id == target_player_id:
            return {"success": False, "error": "Cannot vote to kick yourself"}

        # Add vote
        vote.voters.add(voter_id)

        target_is_host = (target_player_id == self.host_id)
        required_votes = self._get_required_votes(target_is_host)
        current_votes = len(vote.voters)

        # Broadcast vote update
        await self.broadcast({
            "type": "kick_vote_updated",
            "targetPlayerId": target_player_id,
            "currentVotes": current_votes,
            "requiredVotes": required_votes
        })

        print(f"[GameRoom {self.room_id}] Kick vote: {current_votes}/{required_votes} for {vote.target_player_name}")

        # Check if vote passes
        if current_votes >= required_votes:
            await self.kick_player(target_player_id, "Kicked by vote")
            del self.active_kick_votes[target_player_id]
            return {
                "success": True,
                "vote_passed": True
            }

        return {
            "success": True,
            "vote_passed": False,
            "current_votes": current_votes,
            "required_votes": required_votes
        }

    def _get_required_votes(self, target_is_host: bool) -> int:
        """Calculate required votes to kick a player"""
        total_players = len(self.players)

        if target_is_host:
            # Need all other players to vote (unanimous)
            return total_players - 1
        else:
            # Need 2/3 majority (excluding target)
            eligible_voters = total_players - 1
            return max(2, int((eligible_voters * 2) / 3) + 1)

    async def kick_player(self, player_id: str, reason: str = "Kicked"):
        """Kick a player from the room"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        print(f"[GameRoom {self.room_id}] Kicking player {player.name} ({player_id}): {reason}")

        # Close their websocket connection
        try:
            await player.websocket.close(code=1008, reason=reason)
        except Exception as e:
            print(f"[GameRoom {self.room_id}] Error closing websocket for kicked player: {e}")

        # Remove from room
        await self.remove_player(player_id)

        # Broadcast kick event
        await self.broadcast({
            "type": "player_kicked",
            "playerId": player_id,
            "playerName": player.name,
            "reason": reason
        })

        # Clean up any vote for this player
        if player_id in self.active_kick_votes:
            del self.active_kick_votes[player_id]

    def cleanup_expired_votes(self):
        """Remove expired kick votes"""
        now = time.time()
        expired = [
            target_id for target_id, vote in self.active_kick_votes.items()
            if now > vote.expires_at
        ]

        for target_id in expired:
            del self.active_kick_votes[target_id]
            print(f"[GameRoom {self.room_id}] Kick vote expired for player {target_id}")

        return len(expired)

    def is_empty(self) -> bool:
        """Check if the room is empty"""
        return len(self.players) == 0

    def should_hibernate(self) -> bool:
        """Check if room should be hibernated (empty for < hibernation timeout)"""
        if not self.is_empty() or self.is_hibernated:
            return False

        if self._emptied_at is None:
            return False

        # Room has been empty for some time but not long enough to be removed
        empty_duration = time.time() - self._emptied_at
        return empty_duration >= 60  # Hibernate after 1 minute of being empty

    def should_be_removed(self) -> bool:
        """Check if room should be permanently removed"""
        if not self.is_empty():
            return False

        if self._emptied_at is None:
            return False

        # Remove room if empty for longer than hibernation timeout
        empty_duration = time.time() - self._emptied_at
        return empty_duration >= self.HIBERNATION_TIMEOUT_SECONDS

    def get_age_seconds(self) -> float:
        """Get room age in seconds"""
        return time.time() - self._created_at

    def get_empty_duration_seconds(self) -> Optional[float]:
        """Get how long room has been empty, or None if not empty"""
        if self._emptied_at is None:
            return None
        return time.time() - self._emptied_at

    async def hibernate(self):
        """Put room into hibernation mode"""
        if self.is_hibernated or not self.is_empty():
            return

        print(f"[GameRoom {self.room_id}] Entering hibernation mode (age: {self.get_age_seconds():.0f}s)")
        self.is_hibernated = True

        # Could persist room state here if needed
        # For now, we just mark it as hibernated

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
    """
    Manages all game rooms with PartyKit-like lifecycle

    Features:
    - Automatic hibernation of empty rooms after 1 minute
    - Garbage collection of hibernated rooms after 5 minutes
    - Periodic cleanup every 60 seconds
    """

    # Cleanup interval (1 minute)
    CLEANUP_INTERVAL_SECONDS = 60

    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        """Start the room manager and periodic cleanup"""
        if self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_loop())
        print(f"[RoomManager] Started with cleanup interval of {self.CLEANUP_INTERVAL_SECONDS}s")

    async def stop(self):
        """Stop the room manager and cleanup tasks"""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all rooms
        for room_id in list(self.rooms.keys()):
            await self.remove_room(room_id)

        print("[RoomManager] Stopped and cleaned up all rooms")

    async def _periodic_cleanup_loop(self):
        """Periodically clean up and hibernate rooms"""
        while self._is_running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[RoomManager] Error in cleanup loop: {e}")

    async def _run_cleanup(self):
        """Run cleanup and hibernation checks on all rooms"""
        total_rooms = len(self.rooms)
        hibernated_count = 0
        removed_count = 0

        rooms_to_remove = []
        rooms_to_hibernate = []

        # Check each room
        for room_id, room in list(self.rooms.items()):
            if room.should_be_removed():
                rooms_to_remove.append(room_id)
            elif room.should_hibernate():
                rooms_to_hibernate.append((room_id, room))

        # Hibernate rooms
        for room_id, room in rooms_to_hibernate:
            await room.hibernate()
            hibernated_count += 1

        # Remove old rooms
        for room_id in rooms_to_remove:
            await self.remove_room(room_id)
            removed_count += 1

        if hibernated_count > 0 or removed_count > 0:
            print(f"[RoomManager] Cleanup: {total_rooms} total, {hibernated_count} hibernated, {removed_count} removed")

    def get_or_create_room(self, room_id: str) -> GameRoom:
        """Get an existing room or create a new one"""
        if room_id not in self.rooms:
            room = GameRoom(room_id)
            self.rooms[room_id] = room
            asyncio.create_task(room.start_idle_check())
            print(f"[RoomManager] Created new room: {room_id} (total rooms: {len(self.rooms)})")
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
            print(f"[RoomManager] Removed room {room_id} (total rooms: {len(self.rooms)})")

    async def cleanup_empty_rooms(self):
        """Remove empty rooms (called on disconnect for immediate cleanup)"""
        empty_rooms = [
            room_id for room_id, room in self.rooms.items()
            if room.is_empty()
        ]

        for room_id in empty_rooms:
            await self.remove_room(room_id)

    def get_stats(self) -> Dict[str, any]:
        """Get room manager statistics"""
        total_rooms = len(self.rooms)
        active_rooms = sum(1 for room in self.rooms.values() if not room.is_empty())
        hibernated_rooms = sum(1 for room in self.rooms.values() if room.is_hibernated)
        total_players = sum(len(room.players) for room in self.rooms.values())

        return {
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "hibernated_rooms": hibernated_rooms,
            "empty_rooms": total_rooms - active_rooms - hibernated_rooms,
            "total_players": total_players
        }

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
