/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { describe, expect, it } from "vitest";

import GameServer from "../src/server/index";

function createMockConnection(id: string) {
  return { id, send: (_m: string) => {}, close: () => {} };
}

function createMockRoom() {
  const broadcasted: string[] = [];
  return {
    id: "r",
    storage: { setAlarm: async () => {} },
    broadcast: (m: string) => broadcasted.push(m),
    getBroadcasts: () => broadcasted,
  };
}

describe("server pad visibility", () => {
  it("persists pad_visibility from host and includes in room_state", () => {
    const room = createMockRoom();
    const server = new (GameServer as any)(room);

    const c1 = createMockConnection("c1");
    const c2 = createMockConnection("c2");

    server.onMessage(JSON.stringify({ type: "join", playerId: "p1", name: "Host" }), c1);
    server.onMessage(JSON.stringify({ type: "join", playerId: "p2", name: "Player" }), c2);

    server.hostId = "p1";

    server.onMessage(JSON.stringify({ type: "pad_visibility", playerId: "p1", visible: false }), c1);

    expect(server.room.metadata.padVisibility).toBe(false);

    const c3 = createMockConnection("c3");
    let last = "";
    c3.send = (m: string) => {
      last = m;
    };
    server.onConnect(c3);
    const parsed = JSON.parse(last);
    expect(parsed.type).toBe("room_state");
    expect(parsed.padVisibility).toBe(false);
  });
});
