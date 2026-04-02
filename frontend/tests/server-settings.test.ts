import { describe, expect, it } from "vitest";

import GameServer from "../src/server/index";

/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */

// Minimal mock connection
function createMockConnection(id: string) {
  return {
    id,
    send: (_msg: string) => {
      // we can push to an array later if needed
    },
    close: () => {},
  };
}

// Minimal mock room with broadcast and storage
function createMockRoom() {
  const broadcasted: string[] = [];
  return {
    id: "test-room",
    storage: {
      setAlarm: async () => {},
    },
    broadcast: (msg: string) => broadcasted.push(msg),
    getBroadcasts: () => broadcasted,
  };
}

describe("GameServer settings persistence", () => {
  it("persists settings into room.metadata and includes them in room_state on connect", () => {
    const room = createMockRoom();
    const server = new (GameServer as any)(room);

    const conn1 = createMockConnection("c1");
    const conn2 = createMockConnection("c2");

    // Simulate player join messages
    server.onMessage(JSON.stringify({ type: "join", playerId: "p1", name: "Host" }), conn1);
    server.onMessage(JSON.stringify({ type: "join", playerId: "p2", name: "Player" }), conn2);

    // Set host
    server.hostId = "p1";

    // Host sends a settings_update
    const settingsMsg = { type: "settings_update", difficulty: "hard", rounds: 7, roundLength: 90 };
    server.onMessage(JSON.stringify(settingsMsg), conn1);

    // Verify metadata updated
    expect(server.room.metadata.difficulty).toBe("hard");
    expect(server.room.metadata.maxRounds).toBe(7);
    expect(server.room.metadata.roundLength).toBe(90);

    // New connection should receive room_state containing these settings
    const conn3 = createMockConnection("c3");
    // We'll capture what conn3.send would receive by overriding it
    let lastMsg = "";
    conn3.send = (m: string) => {
      lastMsg = m;
    };
    server.onConnect(conn3);

    const parsed = JSON.parse(lastMsg);
    expect(parsed.type).toBe("room_state");
    expect(parsed.difficulty).toBe("hard");
    expect(parsed.maxRounds).toBe(7);
    expect(parsed.roundLength).toBe(90);
  });
});
