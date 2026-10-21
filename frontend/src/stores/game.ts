import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { AVATAR_COLORS, type AvatarColor, getAvatarColor } from "@/composables/useAvatar";
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

export const useGameStore = defineStore(
  "game",
  () => {
    // --- Drawing ---
    const currentStrokes = ref<DrawStroke[]>([]);
    const localPadVisible = ref<boolean>(true);
    const roomPadVisible = ref<boolean>(true);
    // Index into currentStrokes of each remote player's in-progress stroke, so
    // delta fragments append to the same stroke instead of creating a new entry
    // per frame (the source of the old O(n^2) growth).
    const partialStrokeIndex = new Map<string, number>();

    // Prior/completed strokes are hydrated from room_state.lobbyStrokes on join
    // (the server reconstructs them from these same partials). A stroke still in
    // progress exactly at join time may restart on its next fragment — a one-stroke
    // seam, not a permanent gap.
    /** Add a fragment to the player's stroke; returns that stroke's index in currentStrokes. */
    function applyPartialStroke(playerId: string, stroke: DrawStroke, isStart: boolean): number {
      const idx = partialStrokeIndex.get(playerId);
      if (isStart || idx === undefined || !currentStrokes.value[idx]) {
        currentStrokes.value.push({
          color: stroke.color,
          width: stroke.width,
          points: [...stroke.points],
        });
        partialStrokeIndex.set(playerId, currentStrokes.value.length - 1);
        return currentStrokes.value.length - 1;
      }
      currentStrokes.value[idx].points.push(...stroke.points);
      return idx;
    }

    /** Whether the stroke at `index` is a player's latest one, which further fragments may extend. */
    function isLatestStroke(index: number): boolean {
      for (const idx of partialStrokeIndex.values()) if (idx === index) return true;
      return false;
    }

    function clearStrokes() {
      currentStrokes.value = [];
      partialStrokeIndex.clear();
    }

    function setRoomPadVisible(visible: boolean) {
      roomPadVisible.value = visible;
    }

    function setLocalPadVisible(visible: boolean) {
      localPadVisible.value = visible;
    }

    // --- Player identity ---
    const localPlayerId = ref<string>("");
    const localPlayerName = ref<string>("");
    const localPlayerLocale = ref<string>(getBrowserLocale());
    // Null until the player picks one in settings; until then the server picks a
    // colour nobody else in the room has.
    const localPlayerColor = ref<AvatarColor | null>(null);
    const isSpectatorMode = ref<boolean>(false);

    // --- Room & players ---
    const roomCode = ref<string>("");
    // True once the server's authoritative room_state has been applied for the
    // current connection. Gates game views so we never render stale, non-synced
    // state after a reload/reconnect.
    const hydrated = ref<boolean>(false);
    const players = ref<Map<string, Player>>(new Map());
    const hostId = ref<string | null>(null);
    const kickVotes = ref<Map<string, KickVote>>(new Map());

    // --- Game flow ---
    const gamePhase = ref<GamePhase>("lobby");
    const currentRound = ref<number>(0);
    const maxRounds = ref<number>(GAME_SETTINGS.rounds.DEFAULT);
    const difficulty = ref<Difficulty>(GAME_SETTINGS.difficulty.DEFAULT);
    const drawingTimeLimit = ref<number>(GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT);
    const guessingTimeLimit = ref<number>(GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT);
    const roundStartTime = ref<number | undefined>(undefined);
    const guessingStartTime = ref<number | undefined>(undefined);
    const guessTargets = ref<Record<string, string>>({});
    const localPlayerCard = ref<Card | undefined>();
    const lastRoundResults = ref<RoundResult[]>([]);
    const lastHighlights = ref<RoundHighlights | null>(null);
    // Session-only accumulators for the end-of-game gallery + stats. Not persisted
    // (base64 PNGs are large) — rebuilt round-by-round as each round completes.
    const drawingHistory = ref<GalleryDrawing[]>([]);
    const totalGuessesMade = ref<number>(0);
    // Highest round already folded into the gallery/stats. Rounds arrive in order,
    // so this dedupes a resent round_complete even for a round that produced no
    // drawings (where drawingHistory alone would stay empty and re-count).
    const lastCapturedRound = ref<number>(0);
    const readyCount = ref<number>(0);
    const totalPlayers = ref<number>(0);

    // --- Room settings ---
    const defaultLocale = ref<string>("en");
    const isPrivateRoom = ref<boolean>(false);

    // --- Computed ---
    const localPlayer = computed(() => players.value.get(localPlayerId.value));
    // The local player's avatar colour: the one the room assigned (what everyone else sees),
    // else the picked one, else a per-id one.
    const localAvatarColor = computed(
      // The server only assigns colour tokens, so a room colour is an AvatarColor.
      () =>
        (localPlayer.value?.color as AvatarColor | undefined) ??
        localPlayerColor.value ??
        getAvatarColor(localPlayerId.value),
    );
    const playersList = computed(() => Array.from(players.value.values()));
    const canStartGame = computed(() => players.value.size >= 2 && gamePhase.value === "lobby");
    const isHost = computed(() => hostId.value === localPlayerId.value);

    // --- Actions: player identity ---
    function setLocalPlayer(id: string, name: string) {
      localPlayerId.value = id;
      localPlayerName.value = name;
    }

    function setLocalPlayerColor(color: AvatarColor) {
      if (!AVATAR_COLORS.includes(color)) return;
      localPlayerColor.value = color;
    }

    function setSpectatorMode(visible: boolean) {
      isSpectatorMode.value = visible;
    }

    function setLocalPlayerLocale(nextLocale: string) {
      localPlayerLocale.value = nextLocale;
    }

    // --- Actions: room & players ---
    function setRoomCode(code: string) {
      roomCode.value = code;
    }

    function addPlayer(id: string, name: string) {
      if (!players.value.has(id)) {
        players.value.set(id, { id, name, score: 0, color: getAvatarColor(id), connected: true });
      }
      if (players.value.size === 1 && !hostId.value) {
        hostId.value = id;
      }
    }

    function setPlayers(
      nextPlayers: Array<{
        id: string;
        name: string;
        color?: string | null;
        connected?: boolean;
      }>,
    ) {
      const next = new Map<string, Player>();
      for (const incoming of nextPlayers) {
        const existing = players.value.get(incoming.id);
        next.set(incoming.id, {
          id: incoming.id,
          name: incoming.name,
          score: existing?.score ?? 0,
          // The server always sends a colour; the per-id one only fills the nullable contract field.
          color: incoming.color ?? existing?.color ?? getAvatarColor(incoming.id),
          currentCard: existing?.currentCard,
          drawing: existing?.drawing,
          connected: incoming.connected ?? existing?.connected ?? true,
        });
      }
      players.value = next;
      if (players.value.size === 1 && !hostId.value) {
        hostId.value = nextPlayers[0]?.id ?? null;
      }
    }

    function removePlayer(id: string) {
      // Replace with a new Map so Vue's reactivity picks up the change reliably.
      if (players.value.has(id)) {
        const next = new Map(players.value);
        next.delete(id);
        players.value = next;
      }
    }

    function setHost(id: string | null) {
      hostId.value = id;
    }

    // --- Actions: kick votes ---
    function startKickVote(targetPlayerId: string, vote: KickVote) {
      kickVotes.value.set(targetPlayerId, vote);
    }

    function updateKickVote(targetPlayerId: string, data: Pick<KickVote, "currentVotes" | "requiredVotes">) {
      const existing = kickVotes.value.get(targetPlayerId);
      if (existing) {
        existing.currentVotes = data.currentVotes;
        existing.requiredVotes = data.requiredVotes;
      }
    }

    function removeKickVote(targetPlayerId: string) {
      kickVotes.value.delete(targetPlayerId);
    }

    // --- Actions: game flow ---
    // One action per server event that moves the game along, named after the
    // event. The connection handlers only route to these.

    // Every phase change except the return to the lobby opens a fresh ready
    // count. room_state hydration passes the server's counters instead, so live
    // events and reconnects set the phase through the same path.
    function enterPhase(phase: GamePhase, ready = 0, total = players.value.size) {
      gamePhase.value = phase;
      readyCount.value = ready;
      totalPlayers.value = total;
    }

    function onStartGame(
      event: Pick<ServerEventOf<"start_game">, "difficulty" | "rounds" | "drawingTimeLimit" | "guessingTimeLimit">,
    ) {
      difficulty.value = event.difficulty || GAME_SETTINGS.difficulty.DEFAULT;
      maxRounds.value = event.rounds || GAME_SETTINGS.rounds.DEFAULT;
      drawingTimeLimit.value = event.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT;
      guessingTimeLimit.value = event.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT;
      onRestartGame();
    }

    function onStartRound(event: { round?: number | null; cards: Record<string, Card>; roundStartTime?: number }) {
      roundStartTime.value = event.roundStartTime;
      currentRound.value = event.round ?? 1;
      enterPhase("drawing");
      guessingStartTime.value = undefined;
      guessTargets.value = {};
      clearStrokes();
      localPlayerCard.value = undefined;
      for (const [playerId, player] of players.value) {
        player.currentCard = event.cards[playerId];
        player.drawing = undefined;
        if (playerId === localPlayerId.value) {
          localPlayerCard.value = event.cards[playerId];
        }
      }
    }

    function onStartGuessing(event: Pick<ServerEventOf<"start_guessing">, "guessingStartTime" | "guessTargets">) {
      enterPhase("guessing");
      guessingStartTime.value = event.guessingStartTime ?? Date.now();
      guessTargets.value = event.guessTargets ?? {};
    }

    function onRoundComplete(event: {
      results: RoundResult[];
      scores: Record<string, number>;
      highlights?: RoundHighlights | null;
    }) {
      lastRoundResults.value = event.results;
      lastHighlights.value = event.highlights ?? null;
      updateScores(event.scores);
      // Snapshot this round's drawings for the end-of-game gallery before the
      // next start_round clears them. currentRound still names the finished round.
      captureRoundDrawings(currentRound.value);
      enterPhase("round_results");
      // The server starts the next round after its countdown and sends start_round.
    }

    function onGameComplete(event: Pick<ServerEventOf<"game_complete">, "finalScores">) {
      updateScores(event.finalScores);
      enterPhase("final_results");
    }

    // Also applied optimistically by the host when it sends restart_game.
    function onRestartGame() {
      currentRound.value = 0;
      gamePhase.value = "lobby";
      for (const p of players.value.values()) p.score = 0;
      drawingHistory.value = [];
      totalGuessesMade.value = 0;
      lastCapturedRound.value = 0;
    }

    function setReadyStatus(ready: number, total: number) {
      readyCount.value = ready;
      totalPlayers.value = total;
    }

    /**
     * Snapshot the round's drawings into the gallery and fold its correct-guess
     * count into the running total. Called on round_complete while players still
     * hold this round's `.drawing` (startRound clears them on the next round).
     */
    function captureRoundDrawings(round: number) {
      // Idempotent: a resent/duplicate round_complete must not double-list
      // drawings in the gallery or double-count guesses in the running total.
      if (round <= lastCapturedRound.value) return;
      lastCapturedRound.value = round;
      for (const player of players.value.values()) {
        if (player.drawing) {
          drawingHistory.value.push({
            round,
            playerId: player.id,
            name: player.name,
            color: player.color,
            drawing: player.drawing,
          });
        }
      }
      for (const result of lastRoundResults.value) {
        totalGuessesMade.value += result.correctGuesses;
      }
    }

    function updateScores(scores: Record<string, number>) {
      for (const [playerId, score] of Object.entries(scores)) {
        const player = players.value.get(playerId);
        if (player) {
          player.score = score;
        }
      }
    }

    function getFinalScores() {
      return playersList.value
        .map((p) => ({ playerId: p.id, playerName: p.name, score: p.score, color: p.color }))
        .sort((a, b) => b.score - a.score);
    }

    // --- Actions: room settings ---
    function setDefaultLocale(nextLocale: string) {
      defaultLocale.value = nextLocale;
    }

    function setPrivacy(isPrivate: boolean) {
      isPrivateRoom.value = isPrivate;
    }

    function applySettingsUpdate(
      settings: Pick<
        ServerEventOf<"settings_update">,
        "difficulty" | "rounds" | "drawingTimeLimit" | "guessingTimeLimit"
      >,
    ) {
      if (settings.difficulty) difficulty.value = settings.difficulty;
      if (settings.rounds !== null && settings.rounds !== undefined) maxRounds.value = settings.rounds;
      if (settings.drawingTimeLimit !== null && settings.drawingTimeLimit !== undefined) {
        drawingTimeLimit.value = settings.drawingTimeLimit;
      }
      if (settings.guessingTimeLimit !== null && settings.guessingTimeLimit !== undefined) {
        guessingTimeLimit.value = settings.guessingTimeLimit;
      }
    }

    function applyRoomState(roomState: ServerEventOf<"room_state">) {
      setPlayers(roomState.players);
      hostId.value = roomState.hostId ?? null;
      enterPhase(
        roomState.gamePhase,
        roomState.readyCount ?? readyCount.value,
        roomState.totalPlayers ?? totalPlayers.value,
      );
      if (roomState.currentRound !== undefined) currentRound.value = roomState.currentRound;
      applySettingsUpdate({
        difficulty: roomState.difficulty,
        rounds: roomState.maxRounds,
        drawingTimeLimit: roomState.drawingTimeLimit,
        guessingTimeLimit: roomState.guessingTimeLimit,
      });
      roundStartTime.value = roomState.roundStartTime ?? undefined;
      guessingStartTime.value = roomState.guessingStartTime ?? undefined;
      guessTargets.value = roomState.guessTargets ?? {};
      for (const [playerId, playerDrawing] of Object.entries(roomState.drawings ?? {})) {
        setPlayerDrawing(playerId, playerDrawing);
      }
      // Server is authoritative for the round prompt and progress counters, so a
      // mid-round reconnect rehydrates them here rather than from localStorage.
      if (roomState.card) localPlayerCard.value = roomState.card;
      // Rebuild the end-of-game gallery from the server only when we don't already
      // have it (a freshly reconnected client that missed the round_complete
      // events). A fully-connected client builds it incrementally instead.
      if (drawingHistory.value.length === 0 && roomState.drawingHistory?.length) {
        drawingHistory.value = roomState.drawingHistory.map((entry) => ({
          round: entry.round,
          playerId: entry.playerId,
          name: entry.name,
          color: entry.color ?? getAvatarColor(entry.playerId),
          drawing: entry.drawing,
        }));
        // Keep the dedupe cursor in step so a re-delivered round_complete for a
        // round already in the rebuilt gallery isn't folded in a second time.
        lastCapturedRound.value = Math.max(...roomState.drawingHistory.map((e) => e.round), lastCapturedRound.value);
      }
      // Hydrate the shared lobby doodle so a late joiner/reconnect sees the strokes
      // drawn before they arrived, not a blank canvas. Only when we hold none yet,
      // so we never clobber strokes already applied from live partials.
      if (currentStrokes.value.length === 0 && roomState.lobbyStrokes?.length) {
        currentStrokes.value = roomState.lobbyStrokes.map((s) => ({
          color: s.color,
          width: s.width,
          points: [...(s.points ?? [])],
        }));
        partialStrokeIndex.clear();
      }
      if (roomState.padVisibility !== undefined) setRoomPadVisible(roomState.padVisibility);
      if (roomState.defaultLocale) defaultLocale.value = roomState.defaultLocale;
      if (roomState.isPrivate !== undefined) isPrivateRoom.value = roomState.isPrivate;
      // Only treat a snapshot that reflects our own membership (i.e. the one sent
      // after our join completes) as authoritative hydration. A spectator has no
      // membership, so any snapshot hydrates them. This avoids clearing the
      // reconnect gate on the pre-join connect-time snapshot that omits us.
      if (isSpectatorMode.value || roomState.players.some((p) => p.id === localPlayerId.value)) {
        hydrated.value = true;
      }
    }

    // --- Actions: drawing ---
    function setPlayerDrawing(playerId: string, playerDrawing: string) {
      const player = players.value.get(playerId);
      if (player) {
        player.drawing = playerDrawing;
      }
    }

    function setPlayerConnected(playerId: string, connected: boolean) {
      const player = players.value.get(playerId);
      if (player) {
        player.connected = connected;
      }
    }

    // --- Reset ---
    function reset() {
      roomCode.value = "";
      hydrated.value = false;
      players.value.clear();
      kickVotes.value.clear();
      hostId.value = null;
      currentRound.value = 0;
      maxRounds.value = GAME_SETTINGS.rounds.DEFAULT;
      difficulty.value = GAME_SETTINGS.difficulty.DEFAULT;
      gamePhase.value = "lobby";
      roundStartTime.value = undefined;
      guessingStartTime.value = undefined;
      drawingTimeLimit.value = GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT;
      guessingTimeLimit.value = GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT;
      guessTargets.value = {};
      clearStrokes();
      localPlayerCard.value = undefined;
      isSpectatorMode.value = false;
      lastRoundResults.value = [];
      lastHighlights.value = null;
      drawingHistory.value = [];
      totalGuessesMade.value = 0;
      lastCapturedRound.value = 0;
      readyCount.value = 0;
      totalPlayers.value = 0;
      setLocalPadVisible(true);
      setRoomPadVisible(true);
      defaultLocale.value = "en";
      localPlayerLocale.value = getBrowserLocale();
      isPrivateRoom.value = false;
    }

    return {
      // State
      roomCode,
      hydrated,
      localPlayerId,
      localPlayerName,
      players,
      hostId,
      currentRound,
      maxRounds,
      difficulty,
      gamePhase,
      roundStartTime,
      guessingStartTime,
      drawingTimeLimit,
      guessingTimeLimit,
      // Drawing state
      currentStrokes,
      localPadVisible,
      roomPadVisible,
      localPlayerCard,
      isSpectatorMode,
      lastRoundResults,
      lastHighlights,
      drawingHistory,
      totalGuessesMade,
      guessTargets,
      readyCount,
      totalPlayers,
      defaultLocale,
      localPlayerLocale,
      localPlayerColor,
      localAvatarColor,
      kickVotes,
      isPrivateRoom,

      // Computed
      localPlayer,
      playersList,
      canStartGame,
      isHost,

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
  },
  {
    persist: {
      key: STORAGE_KEYS.GAME_STATE,
      // Persist identity + which room we intend to rejoin ONLY. All shared game
      // state (phase, round, timers, guess targets, settings) is server-owned and
      // rehydrated from room_state on (re)connect — persisting it would let a
      // reloaded client render stale, un-synced state. See `hydrated`.
      pick: [
        "localPlayerId",
        "localPlayerName",
        "localPlayerLocale",
        "localPlayerColor",
        "roomCode",
        "defaultLocale",
        "localPadVisible",
      ],
    },
  },
);
