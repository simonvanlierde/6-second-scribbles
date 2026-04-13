import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResultsView from "@/views/ResultsView.vue";

const pushMock = vi.fn();
const sendMock = vi.fn();
const leaveRoomMock = vi.fn();

type FinalScore = {
  playerId: string;
  playerName: string;
  score: number;
};

type StoreMock = {
  localPlayerId: string;
  isHost: boolean;
  gamePhase: string;
  roomCode: string;
  readyCount: number;
  totalPlayers: number;
  maxRounds: number;
  playersList: Array<{ id: string; name: string; score: number }>;
  difficulty: string;
  getFinalScores: ReturnType<typeof vi.fn>;
  resetRound: ReturnType<typeof vi.fn>;
};

let storeMock: StoreMock;

vi.mock("vue-router", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    send: sendMock,
  }),
}));

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({
    leaveRoom: leaveRoomMock,
  }),
}));

vi.mock("@/stores/game", () => ({
  useGameStore: () => storeMock,
}));

function createStoreMock(finalScores: FinalScore[]): StoreMock {
  return {
    localPlayerId: "p1",
    isHost: true,
    gamePhase: "final_results",
    roomCode: "ROOM1",
    readyCount: 0,
    totalPlayers: 0,
    maxRounds: 5,
    playersList: finalScores.map((player) => ({
      id: player.playerId,
      name: player.playerName,
      score: player.score,
    })),
    difficulty: "medium",
    getFinalScores: vi.fn(() => finalScores),
    resetRound: vi.fn(),
  };
}

beforeEach(() => {
  pushMock.mockClear();
  sendMock.mockClear();
  leaveRoomMock.mockClear();
  storeMock = createStoreMock([
    { playerId: "p1", playerName: "Alice", score: 42 },
    { playerId: "p2", playerName: "Bob", score: 42 },
    { playerId: "p3", playerName: "Carol", score: 21 },
  ]);
});

describe("ResultsView", () => {
  it("shows tied winners and shared ranks when the top score is tied", () => {
    const wrapper = mount(ResultsView);

    expect(wrapper.text()).toContain("Winners: Alice and Bob");
    expect(wrapper.text()).toContain("Tied at 42 points");
    expect(wrapper.text()).toContain("Tied for 1st");
    expect(wrapper.findAll(".score-item.winner")).toHaveLength(2);
    expect(wrapper.findAll(".score-item.tied")).toHaveLength(2);
    expect(wrapper.findAll(".rank").map((rank) => rank.text())).toEqual(["1", "1", "3"]);
  });

  it("formats three tied winners with commas", () => {
    storeMock = createStoreMock([
      { playerId: "p1", playerName: "Alice", score: 50 },
      { playerId: "p2", playerName: "Bob", score: 50 },
      { playerId: "p3", playerName: "Carol", score: 50 },
    ]);

    const wrapper = mount(ResultsView);

    expect(wrapper.text()).toContain("Winners: Alice, Bob, Carol");
    expect(wrapper.text()).toContain("Tied at 50 points");
  });
});
