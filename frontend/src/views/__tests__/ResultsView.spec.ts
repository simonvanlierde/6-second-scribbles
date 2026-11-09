import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { GalleryDrawing } from "@/shared/types";
import ResultsView from "@/views/ResultsView.svelte";

const pushMock = vi.fn();
const sendMock = vi.fn();
const playMock = vi.fn();

type FinalScore = { playerId: string; playerName: string; score: number };

type StoreMock = {
  localPlayerId: string;
  localPlayerName: string;
  localPlayerColor: string;
  localAvatarColor: string;
  isHost: boolean;
  gamePhase: string;
  roomCode: string;
  readyCount: number;
  totalPlayers: number;
  maxRounds: number;
  currentRound: number;
  playersList: Array<{
    id: string;
    name: string;
    score: number;
    color?: string | null;
  }>;
  players: Map<string, { id: string; name: string; color?: string | null }>;
  difficulty: string;
  drawingHistory: GalleryDrawing[];
  totalGuessesMade: number;
  getFinalScores: ReturnType<typeof vi.fn>;
  onRestartGame: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
};

let storeMock: StoreMock;

vi.mock("@/router", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock, disconnect: vi.fn() }),
}));

vi.mock("@/composables/useSound.svelte", () => ({
  useSound: () => ({ enabled: { value: false }, play: playMock }),
  SOUND_KEYS: { winner: "winner" },
}));

vi.mock("@/stores/game.svelte", () => ({
  useGameStore: () => storeMock,
}));

function createStoreMock(finalScores: FinalScore[], overrides: Partial<StoreMock> = {}): StoreMock {
  const playersList = finalScores.map((p) => ({
    id: p.playerId,
    name: p.playerName,
    score: p.score,
    color: null,
  }));
  return {
    localPlayerId: "p1",
    localPlayerName: "Alice",
    localPlayerColor: "#ffb4a2",
    localAvatarColor: "#ffb4a2",
    isHost: true,
    gamePhase: "final_results",
    roomCode: "ROOM1",
    readyCount: 0,
    totalPlayers: 0,
    maxRounds: 5,
    currentRound: 5,
    playersList,
    players: new Map(playersList.map((p) => [p.id, p])),
    difficulty: "medium",
    drawingHistory: [],
    totalGuessesMade: 0,
    getFinalScores: vi.fn(() => finalScores),
    onRestartGame: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  pushMock.mockClear();
  sendMock.mockClear();
  playMock.mockClear();
  storeMock = createStoreMock([
    { playerId: "p1", playerName: "Alice", score: 42 },
    { playerId: "p2", playerName: "Bob", score: 21 },
  ]);
});

describe("ResultsView", () => {
  it("renders the winner card with the top scorer", () => {
    const wrapper = render(ResultsView);
    const card = wrapper.container.querySelector(".winner-card")!;
    expect(Boolean(card)).toBe(true);
    expect(card.textContent).toContain("Alice");
    expect(card.textContent).toContain("42 pts");
    expect(card.querySelector(".winner-card__ribbon")?.textContent).toBe("Champion");
  });

  it("shows tied winners with a plural champions ribbon", () => {
    storeMock = createStoreMock([
      { playerId: "p1", playerName: "Alice", score: 42 },
      { playerId: "p2", playerName: "Bob", score: 42 },
    ]);
    const wrapper = render(ResultsView);
    expect(wrapper.container.querySelector(".winner-card__ribbon")?.textContent).toBe("Champions");
    expect(wrapper.container.querySelector(".winner-card")?.textContent).toContain("Alice");
    expect(wrapper.container.querySelector(".winner-card")?.textContent).toContain("Bob");
  });

  it("crowns nobody after a game where nobody scored", () => {
    storeMock = createStoreMock([
      { playerId: "p1", playerName: "Alice", score: 0 },
      { playerId: "p2", playerName: "Bob", score: 0 },
    ]);
    const wrapper = render(ResultsView);
    expect(wrapper.container.querySelector(".winner-card")?.textContent).toContain("No winner this time");
    expect(Boolean(wrapper.container.querySelector(".winner-card__ribbon"))).toBe(false);
  });

  it("shows no ready count in the game-over header", () => {
    const wrapper = render(ResultsView);
    expect(wrapper.container.querySelector(".game-header")?.textContent).not.toMatch(/ready/i);
  });

  it("lists every player in the standings", () => {
    const wrapper = render(ResultsView);
    expect(Array.from(wrapper.container.querySelectorAll(".final-standings__row"))).toHaveLength(2);
  });

  it("shows game stats including drawings and correct guesses", () => {
    storeMock = createStoreMock([{ playerId: "p1", playerName: "Alice", score: 42 }], {
      drawingHistory: [
        {
          round: 1,
          playerId: "p1",
          name: "Alice",
          color: "#fff",
          drawing: "data:,1",
        },
        {
          round: 2,
          playerId: "p1",
          name: "Alice",
          color: "#fff",
          drawing: "data:,2",
        },
      ],
      totalGuessesMade: 7,
    });
    const wrapper = render(ResultsView);
    const stats = wrapper.container.querySelector(".final-stats")?.textContent;
    expect(stats).toContain("2"); // drawings
    expect(stats).toContain("7"); // correct guesses
    expect(stats).toContain("medium"); // difficulty
  });

  it("renders the all-drawings gallery from drawingHistory", () => {
    storeMock = createStoreMock([{ playerId: "p1", playerName: "Alice", score: 42 }], {
      drawingHistory: [
        {
          round: 1,
          playerId: "p1",
          name: "Alice",
          color: "#fff",
          drawing: "data:,1",
        },
      ],
    });
    const wrapper = render(ResultsView);
    expect(Array.from(wrapper.container.querySelectorAll(".gallery__cell"))).toHaveLength(1);
  });

  it("plays the winner stinger once on mount", () => {
    render(ResultsView);
    expect(playMock).toHaveBeenCalledWith("winner");
    expect(playMock).toHaveBeenCalledTimes(1);
  });

  it("host play-again restarts the game", async () => {
    const wrapper = render(ResultsView);
    await fireEvent.click(wrapper.container.querySelector(".final-cta__again")!);
    expect(sendMock).toHaveBeenCalledWith({ type: "restart_game" });
    expect(storeMock.onRestartGame).toHaveBeenCalled();
  });

  it("non-host play-again sends player_ready", async () => {
    storeMock = createStoreMock([{ playerId: "p1", playerName: "Alice", score: 42 }], { isHost: false });
    const wrapper = render(ResultsView);
    await fireEvent.click(wrapper.container.querySelector(".final-cta__again")!);
    expect(sendMock).toHaveBeenCalledWith({
      type: "player_ready",
      playerId: "p1",
    });
  });

  it("back-home leaves immediately when no confirmation is needed", async () => {
    // Single player → useRoomLeave.shouldConfirm is false.
    storeMock = createStoreMock([{ playerId: "p1", playerName: "Alice", score: 42 }]);
    const wrapper = render(ResultsView);
    await fireEvent.click(wrapper.container.querySelector(".final-cta__home")!);
    expect(storeMock.reset).toHaveBeenCalled();
    expect(pushMock).toHaveBeenCalledWith({ name: "home" });
  });

  it("asks the host before they leave others behind from the header", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn(); // jsdom has no modal dialogs
    HTMLDialogElement.prototype.close = vi.fn();
    const wrapper = render(ResultsView);

    await fireEvent.click(wrapper.container.querySelector('[aria-label="Leave"]')!);

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(storeMock.reset).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
