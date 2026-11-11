import { SvelteMap } from "svelte/reactivity";

import { AVATAR_COLORS, type AvatarColor, getAvatarColor } from "@/composables/useAvatar";
import { LOBBY_MAX_POINTS, LOBBY_MAX_STROKE_POINTS, LOBBY_MAX_STROKES } from "@/config/drawing";
import { GAME_SETTINGS, STORAGE_KEYS } from "@/config/gameConfig";
import type { ServerEventOf } from "@/generated/protocol";
import { getBrowserLocale } from "@/shared/locales";
import type {
  Card,
  Difficulty,
  DrawStroke,
  GalleryDrawing,
  GamePhase,
  KickVote,
  Player,
  RoundHighlights,
  RoundResult,
} from "@/shared/types";

function createGameStore() {
  // --- Drawing ---
  // Raw, so Svelte does not walk every point of the doodle on each fragment;
  // strokesVersion counts the changes made inside it.
  let currentStrokes = $state.raw<DrawStroke[]>([]);
  let strokesVersion = $state(0);
  let localPadVisible = $state<boolean>(true);
  let roomPadVisible = $state<boolean>(true);
  // Each player's in-progress stroke, so delta fragments append to it instead of
  // creating a new entry per frame (the source of the old O(n^2) growth).
  const partialStroke = new Map<string, DrawStroke>();
  // Points across currentStrokes, kept as they change, for the doodle cap.
  let strokePoints = 0;

  /** Drop the oldest strokes past the server's caps, as the server does, and forget their owners. */
  function trimStrokes() {
    let drop = 0;
    const strokes = currentStrokes;
    while (
      drop < strokes.length - 1 &&
      (strokes.length - drop > LOBBY_MAX_STROKES || strokePoints > LOBBY_MAX_POINTS)
    ) {
      strokePoints -= (strokes[drop]?.points.length ?? 0) / 2;
      drop++;
    }
    if (drop === 0) return;
    const dropped = new Set(strokes.slice(0, drop));
    currentStrokes = strokes.slice(drop);
    for (const [playerId, stroke] of partialStroke) if (dropped.has(stroke)) partialStroke.delete(playerId);
  }

  // Prior/completed strokes are hydrated from room_state.lobbyStrokes on join
  // (the server reconstructs them from these same partials). A stroke still in
  // progress exactly at join time may restart on its next fragment — a one-stroke
  // seam, not a permanent gap.
  /** Add a fragment to the player's stroke; returns that stroke. */
  function applyPartialStroke(playerId: string, stroke: DrawStroke, isStart: boolean): DrawStroke {
    let target = partialStroke.get(playerId);
    if (isStart || !target) {
      target = { color: stroke.color, width: stroke.width, points: [] };
      currentStrokes.push(target);
      partialStroke.set(playerId, target);
    }
    // The server caps points per stroke, so a stroke never grows without end.
    const room = Math.max(0, LOBBY_MAX_STROKE_POINTS - target.points.length / 2);
    const added = stroke.points.slice(0, room * 2);
    target.points.push(...added);
    strokePoints += added.length / 2;
    trimStrokes();
    strokesVersion++;
    return target;
  }

  /** Whether `stroke` is a player's latest one, which further fragments may extend. */
  function isLatestStroke(stroke: DrawStroke): boolean {
    for (const latest of partialStroke.values()) if (latest === stroke) return true;
    return false;
  }

  function clearStrokes() {
    currentStrokes = [];
    partialStroke.clear();
    strokePoints = 0;
    strokesVersion++;
  }

  function setRoomPadVisible(visible: boolean) {
    roomPadVisible = visible;
  }

  function setLocalPadVisible(visible: boolean) {
    localPadVisible = visible;
  }

  // --- Player identity ---
  let localPlayerId = $state<string>("");
  let localPlayerName = $state<string>("");
  let localPlayerLocale = $state<string>(getBrowserLocale());
  // Null until the player picks one in settings; until then the server picks a
  // colour nobody else in the room has.
  let localPlayerColor = $state<AvatarColor | null>(null);
  let isSpectatorMode = $state<boolean>(false);

  // --- Room & players ---
  let roomCode = $state<string>("");
  // True once the server's authoritative room_state has been applied for the
  // current connection. Gates game views so we never render stale, non-synced
  // state after a reload/reconnect.
  let hydrated = $state<boolean>(false);
  let players = $state<Map<string, Player>>(new SvelteMap());
  let hostId = $state<string | null>(null);
  let kickVotes = $state<Map<string, KickVote>>(new SvelteMap());

  // --- Game flow ---
  let gamePhase = $state<GamePhase>("lobby");
  let currentRound = $state<number>(0);
  let maxRounds = $state<number>(GAME_SETTINGS.rounds.DEFAULT);
  let difficulty = $state<Difficulty>(GAME_SETTINGS.difficulty.DEFAULT);
  let drawingTimeLimit = $state<number>(GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT);
  let guessingTimeLimit = $state<number>(GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT);
  let roundStartTime = $state<number | undefined>(undefined);
  let guessingStartTime = $state<number | undefined>(undefined);
  let guessTargets = $state<Record<string, string>>({});
  let localPlayerCard = $state<Card | undefined>();
  let lastRoundResults = $state<RoundResult[]>([]);
  let lastHighlights = $state<RoundHighlights | null>(null);
  // Session-only accumulators for the end-of-game gallery + stats. Not persisted
  // (base64 PNGs are large) — rebuilt round-by-round as each round completes.
  let drawingHistory = $state<GalleryDrawing[]>([]);
  let totalGuessesMade = $state<number>(0);
  // Highest round already folded into the gallery/stats. Rounds arrive in order,
  // so this dedupes a resent round_complete even for a round that produced no
  // drawings (where drawingHistory alone would stay empty and re-count).
  let lastCapturedRound = $state<number>(0);
  let readyCount = $state<number>(0);
  let totalPlayers = $state<number>(0);

  // --- Room settings ---
  let defaultLocale = $state<string>("en");
  let isPrivateRoom = $state<boolean>(false);

  // --- Computed ---
  let localPlayer = $derived.by(() => players.get(localPlayerId));
  // The local player's avatar colour: the one the room assigned (what everyone else sees),
  // else the picked one, else a per-id one.
  let localAvatarColor = $derived.by(
    // The server only assigns colour tokens, so a room colour is an AvatarColor.
    () => (localPlayer?.color as AvatarColor | undefined) ?? localPlayerColor ?? getAvatarColor(localPlayerId),
  );
  let playersList = $derived.by(() => Array.from(players.values()));
  let canStartGame = $derived.by(() => players.size >= 2 && gamePhase === "lobby");
  let isHost = $derived.by(() => hostId === localPlayerId);

  // --- Actions: player identity ---
  function setLocalPlayer(id: string, name: string) {
    localPlayerId = id;
    localPlayerName = name;
  }

  function setLocalPlayerColor(color: AvatarColor) {
    if (!AVATAR_COLORS.includes(color)) return;
    localPlayerColor = color;
  }

  function setSpectatorMode(visible: boolean) {
    isSpectatorMode = visible;
  }

  function setLocalPlayerLocale(nextLocale: string) {
    localPlayerLocale = nextLocale;
  }

  // --- Actions: room & players ---
  function setRoomCode(code: string) {
    roomCode = code;
  }

  function addPlayer(id: string, name: string) {
    if (!players.has(id)) {
      const player = $state({ id, name, score: 0, color: getAvatarColor(id), connected: true });
      players.set(id, player);
    }
    if (players.size === 1 && !hostId) {
      hostId = id;
    }
  }

  function setPlayers(
    nextPlayers: Array<{
      id: string;
      name: string;
      score?: number;
      color?: string | null;
      connected?: boolean;
    }>,
  ) {
    const next = new SvelteMap<string, Player>();
    for (const incoming of nextPlayers) {
      const existing = players.get(incoming.id);
      const player = $state<Player>({
        id: incoming.id,
        name: incoming.name,
        score: incoming.score ?? existing?.score ?? 0,
        // The server always sends a colour; the per-id one only fills the nullable contract field.
        color: incoming.color ?? existing?.color ?? getAvatarColor(incoming.id),
        currentCard: existing?.currentCard,
        drawing: existing?.drawing,
        connected: incoming.connected ?? existing?.connected ?? true,
      });
      next.set(incoming.id, player);
    }
    players = next;
    if (players.size === 1 && !hostId) {
      hostId = nextPlayers[0]?.id ?? null;
    }
  }

  function removePlayer(id: string) {
    // Replace the map to publish the changed roster.
    if (players.has(id)) {
      const next = new SvelteMap(players);
      next.delete(id);
      players = next;
    }
  }

  function setHost(id: string | null) {
    hostId = id;
  }

  // --- Actions: kick votes ---
  function startKickVote(targetPlayerId: string, vote: KickVote) {
    const reactiveVote = $state({ ...vote });
    kickVotes.set(targetPlayerId, reactiveVote);
  }

  function updateKickVote(targetPlayerId: string, data: Pick<KickVote, "currentVotes" | "requiredVotes">) {
    const existing = kickVotes.get(targetPlayerId);
    if (existing) {
      existing.currentVotes = data.currentVotes;
      existing.requiredVotes = data.requiredVotes;
    }
  }

  function removeKickVote(targetPlayerId: string) {
    kickVotes.delete(targetPlayerId);
  }

  // --- Actions: game flow ---
  // One action per server event that moves the game along, named after the
  // event. The connection handlers only route to these.

  // Every phase change except the return to the lobby opens a fresh ready
  // count. room_state hydration passes the server's counters instead, so live
  // events and reconnects set the phase through the same path.
  function enterPhase(phase: GamePhase, ready = 0, total = players.size) {
    gamePhase = phase;
    readyCount = ready;
    totalPlayers = total;
  }

  function onStartGame(
    event: Pick<ServerEventOf<"start_game">, "difficulty" | "rounds" | "drawingTimeLimit" | "guessingTimeLimit">,
  ) {
    difficulty = event.difficulty || GAME_SETTINGS.difficulty.DEFAULT;
    maxRounds = event.rounds || GAME_SETTINGS.rounds.DEFAULT;
    drawingTimeLimit = event.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT;
    guessingTimeLimit = event.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT;
    onRestartGame();
  }

  function onStartRound(event: { round?: number | null; cards: Record<string, Card>; roundStartTime?: number }) {
    roundStartTime = event.roundStartTime;
    currentRound = event.round ?? 1;
    enterPhase("drawing");
    guessingStartTime = undefined;
    guessTargets = {};
    clearStrokes();
    localPlayerCard = undefined;
    for (const [playerId, player] of players) {
      player.currentCard = event.cards[playerId];
      player.drawing = undefined;
      if (playerId === localPlayerId) {
        localPlayerCard = event.cards[playerId];
      }
    }
  }

  function onStartGuessing(event: Pick<ServerEventOf<"start_guessing">, "guessingStartTime" | "guessTargets">) {
    enterPhase("guessing");
    guessingStartTime = event.guessingStartTime ?? Date.now();
    guessTargets = event.guessTargets ?? {};
  }

  function onRoundComplete(event: {
    results: RoundResult[];
    scores: Record<string, number>;
    highlights?: RoundHighlights | null;
  }) {
    lastRoundResults = event.results;
    lastHighlights = event.highlights ?? null;
    updateScores(event.scores);
    // Snapshot this round's drawings for the end-of-game gallery before the
    // next start_round clears them. currentRound still names the finished round.
    captureRoundDrawings(currentRound);
    enterPhase("round_results");
    // The server starts the next round after its countdown and sends start_round.
  }

  function onGameComplete(event: Pick<ServerEventOf<"game_complete">, "finalScores">) {
    updateScores(event.finalScores);
    enterPhase("final_results");
  }

  // Also applied optimistically by the host when it sends restart_game.
  function onRestartGame() {
    currentRound = 0;
    gamePhase = "lobby";
    for (const p of players.values()) p.score = 0;
    drawingHistory = [];
    totalGuessesMade = 0;
    lastCapturedRound = 0;
  }

  function setReadyStatus(ready: number, total: number) {
    readyCount = ready;
    totalPlayers = total;
  }

  /**
   * Snapshot the round's drawings into the gallery and fold its correct-guess
   * count into the running total. Called on round_complete while players still
   * hold this round's `.drawing` (startRound clears them on the next round).
   */
  function captureRoundDrawings(round: number) {
    // Idempotent: a resent/duplicate round_complete must not double-list
    // drawings in the gallery or double-count guesses in the running total.
    if (round <= lastCapturedRound) return;
    lastCapturedRound = round;
    for (const player of players.values()) {
      if (player.drawing) {
        drawingHistory.push({
          round,
          playerId: player.id,
          name: player.name,
          color: player.color,
          drawing: player.drawing,
        });
      }
    }
    for (const result of lastRoundResults) {
      totalGuessesMade += result.correctGuesses;
    }
  }

  function updateScores(scores: Record<string, number>) {
    for (const [playerId, score] of Object.entries(scores)) {
      const player = players.get(playerId);
      if (player) {
        player.score = score;
      }
    }
  }

  function getFinalScores() {
    return playersList
      .map((p) => ({ playerId: p.id, playerName: p.name, score: p.score, color: p.color }))
      .sort((a, b) => b.score - a.score);
  }

  // --- Actions: room settings ---
  function setDefaultLocale(nextLocale: string) {
    defaultLocale = nextLocale;
  }

  function setPrivacy(isPrivate: boolean) {
    isPrivateRoom = isPrivate;
  }

  function applySettingsUpdate(
    settings: Pick<
      ServerEventOf<"settings_update">,
      "difficulty" | "rounds" | "drawingTimeLimit" | "guessingTimeLimit"
    >,
  ) {
    if (settings.difficulty) difficulty = settings.difficulty;
    if (settings.rounds !== null && settings.rounds !== undefined) maxRounds = settings.rounds;
    if (settings.drawingTimeLimit !== null && settings.drawingTimeLimit !== undefined) {
      drawingTimeLimit = settings.drawingTimeLimit;
    }
    if (settings.guessingTimeLimit !== null && settings.guessingTimeLimit !== undefined) {
      guessingTimeLimit = settings.guessingTimeLimit;
    }
  }

  function applyRoomState(roomState: ServerEventOf<"room_state">) {
    setPlayers(roomState.players);
    hostId = roomState.hostId ?? null;
    enterPhase(roomState.gamePhase, roomState.readyCount ?? readyCount, roomState.totalPlayers ?? totalPlayers);
    if (roomState.currentRound !== undefined) currentRound = roomState.currentRound;
    applySettingsUpdate({
      difficulty: roomState.difficulty,
      rounds: roomState.maxRounds,
      drawingTimeLimit: roomState.drawingTimeLimit,
      guessingTimeLimit: roomState.guessingTimeLimit,
    });
    roundStartTime = roomState.roundStartTime ?? undefined;
    guessingStartTime = roomState.guessingStartTime ?? undefined;
    guessTargets = roomState.guessTargets ?? {};
    for (const [playerId, playerDrawing] of Object.entries(roomState.drawings ?? {})) {
      setPlayerDrawing(playerId, playerDrawing);
    }
    // Server is authoritative for the round prompt and progress counters, so a
    // mid-round reconnect rehydrates them here rather than from localStorage.
    if (roomState.card) localPlayerCard = roomState.card;
    // Rebuild the end-of-game gallery from the server only when we don't already
    // have it (a freshly reconnected client that missed the round_complete
    // events). A fully-connected client builds it incrementally instead.
    if (drawingHistory.length === 0 && roomState.drawingHistory?.length) {
      drawingHistory = roomState.drawingHistory.map((entry) => ({
        round: entry.round,
        playerId: entry.playerId,
        name: entry.name,
        color: entry.color ?? getAvatarColor(entry.playerId),
        drawing: entry.drawing,
      }));
      // Keep the dedupe cursor in step so a re-delivered round_complete for a
      // round already in the rebuilt gallery isn't folded in a second time.
      lastCapturedRound = Math.max(...roomState.drawingHistory.map((e) => e.round), lastCapturedRound);
    }
    // Hydrate the shared lobby doodle so a late joiner/reconnect sees the strokes
    // drawn before they arrived, not a blank canvas. Only when we hold none yet,
    // so we never clobber strokes already applied from live partials.
    if (currentStrokes.length === 0 && roomState.lobbyStrokes?.length) {
      currentStrokes = roomState.lobbyStrokes.map((s) => ({
        color: s.color,
        width: s.width,
        points: [...(s.points ?? [])],
      }));
      partialStroke.clear();
      strokePoints = currentStrokes.reduce((sum, s) => sum + s.points.length / 2, 0);
      trimStrokes();
      strokesVersion++;
    }
    if (roomState.padVisibility !== undefined) setRoomPadVisible(roomState.padVisibility);
    if (roomState.defaultLocale) defaultLocale = roomState.defaultLocale;
    if (roomState.isPrivate !== undefined) isPrivateRoom = roomState.isPrivate;
    // Only treat a snapshot that reflects our own membership (i.e. the one sent
    // after our join completes) as authoritative hydration. A spectator has no
    // membership, so any snapshot hydrates them. This avoids clearing the
    // reconnect gate on the pre-join connect-time snapshot that omits us.
    if (isSpectatorMode || roomState.players.some((p) => p.id === localPlayerId)) {
      hydrated = true;
    }
  }

  // --- Actions: drawing ---
  function setPlayerDrawing(playerId: string, playerDrawing: string) {
    const player = players.get(playerId);
    if (player) {
      player.drawing = playerDrawing;
    }
  }

  function setPlayerConnected(playerId: string, connected: boolean) {
    const player = players.get(playerId);
    if (player) {
      player.connected = connected;
    }
  }

  // --- Reset ---
  function reset() {
    roomCode = "";
    hydrated = false;
    players.clear();
    kickVotes.clear();
    hostId = null;
    currentRound = 0;
    maxRounds = GAME_SETTINGS.rounds.DEFAULT;
    difficulty = GAME_SETTINGS.difficulty.DEFAULT;
    gamePhase = "lobby";
    roundStartTime = undefined;
    guessingStartTime = undefined;
    drawingTimeLimit = GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT;
    guessingTimeLimit = GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT;
    guessTargets = {};
    clearStrokes();
    localPlayerCard = undefined;
    isSpectatorMode = false;
    lastRoundResults = [];
    lastHighlights = null;
    drawingHistory = [];
    totalGuessesMade = 0;
    lastCapturedRound = 0;
    readyCount = 0;
    totalPlayers = 0;
    setLocalPadVisible(true);
    setRoomPadVisible(true);
    defaultLocale = "en";
    localPlayerLocale = getBrowserLocale();
    isPrivateRoom = false;
  }

  return {
    // State
    get roomCode() {
      return roomCode;
    },
    set roomCode(value) {
      roomCode = value;
    },
    get hydrated() {
      return hydrated;
    },
    set hydrated(value) {
      hydrated = value;
    },
    get localPlayerId() {
      return localPlayerId;
    },
    set localPlayerId(value) {
      localPlayerId = value;
    },
    get localPlayerName() {
      return localPlayerName;
    },
    set localPlayerName(value) {
      localPlayerName = value;
    },
    get players() {
      return players;
    },
    set players(value) {
      players = value;
    },
    get hostId() {
      return hostId;
    },
    set hostId(value) {
      hostId = value;
    },
    get currentRound() {
      return currentRound;
    },
    set currentRound(value) {
      currentRound = value;
    },
    get maxRounds() {
      return maxRounds;
    },
    set maxRounds(value) {
      maxRounds = value;
    },
    get difficulty() {
      return difficulty;
    },
    set difficulty(value) {
      difficulty = value;
    },
    get gamePhase() {
      return gamePhase;
    },
    set gamePhase(value) {
      gamePhase = value;
    },
    get roundStartTime() {
      return roundStartTime;
    },
    set roundStartTime(value) {
      roundStartTime = value;
    },
    get guessingStartTime() {
      return guessingStartTime;
    },
    set guessingStartTime(value) {
      guessingStartTime = value;
    },
    get drawingTimeLimit() {
      return drawingTimeLimit;
    },
    set drawingTimeLimit(value) {
      drawingTimeLimit = value;
    },
    get guessingTimeLimit() {
      return guessingTimeLimit;
    },
    set guessingTimeLimit(value) {
      guessingTimeLimit = value;
    },
    // Drawing state
    get currentStrokes() {
      return currentStrokes;
    },
    set currentStrokes(value) {
      currentStrokes = value;
    },
    get strokesVersion() {
      return strokesVersion;
    },
    set strokesVersion(value) {
      strokesVersion = value;
    },
    get localPadVisible() {
      return localPadVisible;
    },
    set localPadVisible(value) {
      localPadVisible = value;
    },
    get roomPadVisible() {
      return roomPadVisible;
    },
    set roomPadVisible(value) {
      roomPadVisible = value;
    },
    get localPlayerCard() {
      return localPlayerCard;
    },
    set localPlayerCard(value) {
      localPlayerCard = value;
    },
    get isSpectatorMode() {
      return isSpectatorMode;
    },
    set isSpectatorMode(value) {
      isSpectatorMode = value;
    },
    get lastRoundResults() {
      return lastRoundResults;
    },
    set lastRoundResults(value) {
      lastRoundResults = value;
    },
    get lastHighlights() {
      return lastHighlights;
    },
    set lastHighlights(value) {
      lastHighlights = value;
    },
    get drawingHistory() {
      return drawingHistory;
    },
    set drawingHistory(value) {
      drawingHistory = value;
    },
    get totalGuessesMade() {
      return totalGuessesMade;
    },
    set totalGuessesMade(value) {
      totalGuessesMade = value;
    },
    get guessTargets() {
      return guessTargets;
    },
    set guessTargets(value) {
      guessTargets = value;
    },
    get readyCount() {
      return readyCount;
    },
    set readyCount(value) {
      readyCount = value;
    },
    get totalPlayers() {
      return totalPlayers;
    },
    set totalPlayers(value) {
      totalPlayers = value;
    },
    get defaultLocale() {
      return defaultLocale;
    },
    set defaultLocale(value) {
      defaultLocale = value;
    },
    get localPlayerLocale() {
      return localPlayerLocale;
    },
    set localPlayerLocale(value) {
      localPlayerLocale = value;
    },
    get localPlayerColor() {
      return localPlayerColor;
    },
    set localPlayerColor(value) {
      localPlayerColor = value;
    },
    get localAvatarColor() {
      return localAvatarColor;
    },
    get kickVotes() {
      return kickVotes;
    },
    set kickVotes(value) {
      kickVotes = value;
    },
    get isPrivateRoom() {
      return isPrivateRoom;
    },
    set isPrivateRoom(value) {
      isPrivateRoom = value;
    },

    // Computed
    get localPlayer() {
      return localPlayer;
    },
    get playersList() {
      return playersList;
    },
    get canStartGame() {
      return canStartGame;
    },
    get isHost() {
      return isHost;
    },

    // Actions
    setLocalPlayer,
    setSpectatorMode,
    setLocalPlayerLocale,
    setLocalPlayerColor,
    setRoomCode,
    addPlayer,
    setPlayers,
    removePlayer,
    setHost,
    startKickVote,
    updateKickVote,
    removeKickVote,
    onStartGame,
    onStartRound,
    onStartGuessing,
    onRoundComplete,
    onGameComplete,
    onRestartGame,
    setReadyStatus,
    getFinalScores,
    setDefaultLocale,
    setPrivacy,
    applySettingsUpdate,
    applyRoomState,
    // Drawing actions
    applyPartialStroke,
    isLatestStroke,
    clearStrokes,
    setPlayerDrawing,
    setPlayerConnected,
    setRoomPadVisible,
    setLocalPadVisible,
    reset,
  };
}

const game = createGameStore();
const persistedKeys = [
  "localPlayerId",
  "localPlayerName",
  "localPlayerLocale",
  "localPlayerColor",
  "roomCode",
  "defaultLocale",
  "localPadVisible",
] as const;
try {
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.GAME_STATE) ?? "{}");
  for (const key of persistedKeys) {
    if (
      key === "localPlayerColor"
        ? saved[key] === null || AVATAR_COLORS.includes(saved[key])
        : typeof saved[key] === typeof game[key]
    ) {
      Object.assign(game, { [key]: saved[key] });
    }
  }
} catch {
  /* Storage unavailable or invalid. */
}
$effect.root(() => {
  $effect(() => {
    const saved = Object.fromEntries(persistedKeys.map((key) => [key, game[key]]));
    try {
      localStorage.setItem(STORAGE_KEYS.GAME_STATE, JSON.stringify(saved));
    } catch {
      /* Storage unavailable. */
    }
  });
});
export function useGameStore() {
  return game;
}
