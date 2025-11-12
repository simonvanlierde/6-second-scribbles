/**
 * Partykit Server for Six Second Scribbles
 *
 * Architecture: "Dumb Pipe" Pattern
 * - Server only relays messages between clients
 * - All game logic lives in client-side GameEngine
 * - Easy to migrate to FastAPI/custom backend later
 */

import type * as Party from "partykit/server";

// Message types (shared contract between client and server)
export type GameMessage =
  | { type: "join"; playerId: string; name: string }
  | { type: "player_joined"; playerId: string; name: string; players: Array<{ id: string; name: string }> }
  | { type: "player_left"; playerId: string }
  | { type: "host_changed"; newHostId: string }
  | { type: "start_game"; difficulty: string; rounds: number; roundLength: number }
  | { type: "start_round"; round: number; roundStartTime: number; cards: Record<string, { category: string; items: string[] }> }
  | { type: "submit_guess"; playerId: string; targetPlayerId: string; guesses: string[] }
  | { type: "round_complete"; scores: Record<string, number> }
  | { type: "game_complete"; finalScores: Record<string, number> }
  | { type: "request_game_state"; playerId: string }
  | { type: "player_ready"; playerId: string }
  | { type: "restart_game" }
  | { type: "heartbeat"; playerId: string }
  | { type: "settings_update"; difficulty: string; rounds: number; roundLength: number }
  | { type: 'draw_stroke'; playerId: string; stroke: { color: string; width: number; points: Array<{ x: number; y: number }> } }
  | { type: 'drawpad_clear'; playerId: string }
  | { type: 'draw_stroke_partial'; playerId: string; stroke: { color: string; width: number; points: Array<{ x: number; y: number }> } }
  | { type: 'pad_visibility'; playerId: string; visible: boolean };

interface Player {
  id: string;
  name: string;
  connection: Party.Connection;
  categories: string[]; // Added categories to Player
  lastActivity: number; // Unix timestamp of last activity
}

// Define metadata property on the Room type
interface RoomMetadata {
  categories: string[];
  gamePhase: string;
  roundStartTime?: number; // Unix timestamp when current round started (server-generated)
  roundLength?: number; // Duration of each round in seconds (host-configured)
  difficulty?: string;
  maxRounds?: number;
    padVisibility?: boolean;
  readyPlayers: Set<string>; // Players ready for next game
}

// Extend the Party.Room type to include metadata
interface ExtendedRoom extends Party.Room {
  metadata: RoomMetadata;
}

export default class GameServer implements Party.Server {
  players: Map<string, Player> = new Map();
  hostId: string | null = null;
  room: ExtendedRoom;

  // Idle timeout configuration (3 minutes of inactivity during game)
  static readonly IDLE_TIMEOUT_MS = 3 * 60 * 1000;

  constructor(room: Party.Room) {
    this.room = room as ExtendedRoom;
    this.room.metadata = {
      categories: [],
      gamePhase: "lobby", // Unified initial state
      difficulty: 'medium',
      maxRounds: 5,
        padVisibility: true,
      readyPlayers: new Set(),
    };

    // Schedule periodic idle check every 60 seconds
    this.room.storage.setAlarm(Date.now() + 60000);
  }

  async onAlarm() {
    // Check for idle players only during active game phases
    if (this.room.metadata.gamePhase !== 'lobby' && this.room.metadata.gamePhase !== 'complete') {
      const now = Date.now();
      const idlePlayers: string[] = [];

      for (const [playerId, player] of this.players.entries()) {
        const idleTime = now - player.lastActivity;
        if (idleTime > GameServer.IDLE_TIMEOUT_MS) {
          console.log(`[Server] Player ${player.name} (${playerId}) is idle for ${Math.floor(idleTime / 1000)}s`);
          idlePlayers.push(playerId);
        }
      }

      // Disconnect idle players
      for (const playerId of idlePlayers) {
        const player = this.players.get(playerId);
        if (player) {
          console.log(`[Server] Disconnecting idle player: ${player.name}`);
          player.connection.close(1000, 'Disconnected due to inactivity');
        }
      }
    }

    // Schedule next check
    await this.room.storage.setAlarm(Date.now() + 60000);
  }

  onConnect(conn: Party.Connection) {
    console.log(`Connection ${conn.id} connected to room ${this.room.id}`);

    // Send current players, categories, game phase, and timing info to new connection
    const currentPlayers = Array.from(this.players.values()).map((p) => ({
      id: p.id,
      name: p.name,
    }));

    conn.send(
      JSON.stringify({
        type: "room_state",
        players: currentPlayers,
        categories: this.room.metadata.categories,
        gamePhase: this.room.metadata.gamePhase,
        roundStartTime: this.room.metadata.roundStartTime,
        roundLength: this.room.metadata.roundLength,
        difficulty: this.room.metadata.difficulty,
        maxRounds: this.room.metadata.maxRounds,
        padVisibility: this.room.metadata.padVisibility,
      })
    );
  }

  onMessage(message: string, sender: Party.Connection) {
    try {
      const msg: GameMessage = JSON.parse(message);

      // Update last activity for the sender (except for join messages, handled separately)
      if (msg.type !== 'join') {
        for (const player of this.players.values()) {
          if (player.connection.id === sender.id) {
            player.lastActivity = Date.now();
            break;
          }
        }
      }

      // Handle join specially to track players
      if (msg.type === "join") {
        this.players.set(msg.playerId, {
          id: msg.playerId,
          name: msg.name,
          connection: sender,
          categories: this.generateCategoriesForPlayer(), // Assign categories on join
          lastActivity: Date.now(),
        });

        // If this is the first player, make them host
        if (this.players.size === 1) {
          this.hostId = msg.playerId;
        }

        // Broadcast updated player list to everyone
        const allPlayers = Array.from(this.players.values()).map((p) => ({
          id: p.id,
          name: p.name,
        }));

        console.log('[Server] Broadcasting player_joined with players:', allPlayers);

        this.room.broadcast(
          JSON.stringify({
            type: "player_joined",
            playerId: msg.playerId,
            name: msg.name,
            players: allPlayers,
          })
        );

        return;
      }

      // Handle start_game: Store roundLength, relay to all clients
      if (msg.type === "start_game") {
        console.log('[Server] Raw start_game message:', JSON.stringify(msg));

        const playerCount = this.players.size;
        if (playerCount < 2) {
          console.error('[Server] Cannot start game: Not enough players. Current player count:', playerCount);
          return;
        }

        // Prevent duplicate processing
        if (this.room.metadata.gamePhase !== 'lobby') {
          console.warn('[Server] Ignoring start_game message - game already started.');
          return;
        }

        // Store roundLength from host client
  this.room.metadata.roundLength = msg.roundLength;
  this.room.metadata.difficulty = msg.difficulty;
  this.room.metadata.maxRounds = msg.rounds;
        this.room.metadata.gamePhase = "drawing";

        // Clear ready players when game starts
        this.room.metadata.readyPlayers.clear();

        console.log(`[Server] Game configured with round length: ${msg.roundLength} seconds`);

        // Just relay the start_game message to all clients
        // Host client's game engine will handle starting the first round
        this.room.broadcast(message);
        return;
      }

      // Handle start_round: Generate roundStartTime and broadcast
      if (msg.type === "start_round") {
        const roundStartTime = Date.now();
        this.room.metadata.roundStartTime = roundStartTime;
        this.room.metadata.gamePhase = "drawing";

        // Clear ready players when starting a new round
        this.room.metadata.readyPlayers.clear();

        console.log(`[Server] Starting round ${msg.round} at ${roundStartTime}`);

        // Broadcast start_round with server-generated roundStartTime
        this.room.broadcast(
          JSON.stringify({
            ...msg,
            roundStartTime,
          })
        );
        return;
      }

      if (msg.type === "round_complete") {
        this.room.metadata.gamePhase = "scoring";
      }

      if (msg.type === "game_complete") {
        this.room.metadata.gamePhase = "complete";
        // Clear ready players when game completes
        this.room.metadata.readyPlayers.clear();
      }

      // Handle player_ready: Track ready players for post-game
      if (msg.type === "player_ready") {
        this.room.metadata.readyPlayers.add(msg.playerId);
        console.log(`[Server] Player ${msg.playerId} is ready. Ready count: ${this.room.metadata.readyPlayers.size}/${this.players.size}`);

        // Broadcast ready status to all players
        this.room.broadcast(
          JSON.stringify({
            type: "ready_status",
            readyCount: this.room.metadata.readyPlayers.size,
            totalPlayers: this.players.size,
          })
        );
        return;
      }

      // Handle restart_game: Reset game state and notify all players
      if (msg.type === "restart_game") {
        console.log('[Server] Host initiated game restart');

        // Reset ready players
        this.room.metadata.readyPlayers.clear();

        // Reset game phase to lobby
        this.room.metadata.gamePhase = "lobby";

        // Broadcast restart to all players so they navigate to waiting room
        this.room.broadcast(message);
        return;
      }

      // Handle heartbeat: Just update last activity (already done above)
      if (msg.type === "heartbeat") {
        // Activity already updated above, no need to broadcast
        return;
      }

      // Handle settings_update: Host broadcasts settings changes to all players
      if (msg.type === "settings_update") {
        // Find the playerId associated with the sender connection
        let senderPlayerId: string | null = null;
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid;
            break;
          }
        }

        // Only allow the current host to broadcast settings updates
        if (senderPlayerId && this.hostId && senderPlayerId === this.hostId) {
          // Persist the settings in room metadata so new joiners receive them
          this.room.metadata.difficulty = msg.difficulty;
          this.room.metadata.maxRounds = msg.rounds;
          this.room.metadata.roundLength = msg.roundLength;

          console.log('[Server] Broadcasting settings update from host:', msg);
          this.room.broadcast(message);
        } else {
          console.warn('[Server] Ignored settings_update from non-host connection', sender.id);
        }

        return;
      }

      // Handle draw_stroke: Relay stroke data to all clients (including sender)
      if (msg.type === 'draw_stroke') {
        // Optional: We could validate senderPlayerId here but allowing all players to draw in waiting room
        this.room.broadcast(message);
        return;
      }

      // Handle draw_stroke_partial: Relay incremental stroke points to all clients
      if (msg.type === 'draw_stroke_partial') {
        this.room.broadcast(message);
        return;
      }

      // Handle drawpad_clear: Only allow host to clear the shared waiting-room pad
      if (msg.type === 'drawpad_clear') {
        // Find the playerId associated with the sender connection
        let senderPlayerId: string | null = null;
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid;
            break;
          }
        }

        if (senderPlayerId && this.hostId && senderPlayerId === this.hostId) {
          console.log('[Server] Host cleared drawpad');
          this.room.broadcast(message);
        } else {
          console.warn('[Server] Ignored drawpad_clear from non-host connection', sender.id);
        }

        return;
      }

      // Handle pad_visibility: Only allow host to change visibility
      if (msg.type === 'pad_visibility') {
        let senderPlayerId: string | null = null;
        for (const [pid, player] of this.players.entries()) {
          if (player.connection.id === sender.id) {
            senderPlayerId = pid;
            break;
          }
        }

        if (senderPlayerId && this.hostId && senderPlayerId === this.hostId) {
          this.room.metadata.padVisibility = (msg as any).visible
          console.log('[Server] Host updated pad visibility to', (msg as any).visible)
          this.room.broadcast(message)
        } else {
          console.warn('[Server] Ignored pad_visibility from non-host connection', sender.id)
        }

        return;
      }

      // Handle request_game_state to send the current game state to the requester
      if (msg.type === "request_game_state") {
        const currentPlayers = Array.from(this.players.values()).map((p) => ({
          id: p.id,
          name: p.name,
          categories: p.categories, // Include categories in room_state
        }));

        sender.send(
          JSON.stringify({
            type: "room_state",
            players: currentPlayers,
            categories: this.room.metadata.categories,
            gamePhase: this.room.metadata.gamePhase,
            roundStartTime: this.room.metadata.roundStartTime,
            roundLength: this.room.metadata.roundLength,
          })
        );

        return;
      }

      // For all other messages, just relay to all clients including sender
      // (Game logic is handled client-side)
      this.room.broadcast(message);
    } catch (error) {
      console.error("Error processing message:", error);
    }
  }

  onClose(connection: Party.Connection) {
    // Remove player when they disconnect
    let disconnectedPlayerId: string | null = null;

    for (const [playerId, player] of this.players.entries()) {
      if (player.connection.id === connection.id) {
        disconnectedPlayerId = playerId;
        this.players.delete(playerId);

        // Notify others
        this.room.broadcast(JSON.stringify({
          type: "player_left",
          playerId: playerId
        }));

        break;
      }
    }

    // Handle host transfer if the host left
    if (disconnectedPlayerId === this.hostId) {
      if (this.players.size > 0) {
        // Transfer host to the next player (first in the map)
        const newHost = Array.from(this.players.values())[0];
        if (newHost) {
          this.hostId = newHost.id;

          // Notify all remaining players of the new host
          this.room.broadcast(JSON.stringify({
            type: "host_changed",
            newHostId: newHost.id,
          }));

          console.log(`Host transferred to ${newHost.name} (${newHost.id})`);
        }
      } else {
        // No players left, room is effectively closed
        this.hostId = null;
        console.log(`Room ${this.room.id} is now empty`);
      }
    }
  }

  onError(_connection: Party.Connection, error: Error) {
    console.error("Connection error:", error);
  }

  // Helper function to generate categories for a player
  private generateCategoriesForPlayer(): string[] {
    // Replace with actual category generation logic
    return ["Category1", "Category2", "Category3"];
  }
}

GameServer satisfies Party.Worker;
