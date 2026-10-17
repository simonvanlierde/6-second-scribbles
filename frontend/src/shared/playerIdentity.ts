import { STORAGE_KEYS } from "@/config/gameConfig";

function getOrCreateStored(key: string): string {
  try {
    const existing = localStorage.getItem(key);
    if (existing) return existing;

    const created = crypto.randomUUID();
    localStorage.setItem(key, created);
    return created;
  } catch {
    return crypto.randomUUID();
  }
}

export function getOrCreatePlayerId(): string {
  return getOrCreateStored(STORAGE_KEYS.PLAYER_ID);
}

let rejoinKey: string | undefined;

/** Secret sent with every join: player ids are public, so this proves a reconnect is the same browser. */
export function getRejoinKey(): string {
  // Cached so a page without localStorage still sends one stable key across reconnects.
  rejoinKey ??= getOrCreateStored(STORAGE_KEYS.REJOIN_KEY);
  return rejoinKey;
}
