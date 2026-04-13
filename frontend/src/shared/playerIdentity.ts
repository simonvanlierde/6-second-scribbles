import { STORAGE_KEYS } from "@/config/gameConfig";

export function getOrCreatePlayerId(): string {
  try {
    const existingId = localStorage.getItem(STORAGE_KEYS.PLAYER_ID);
    if (existingId) return existingId;

    const newId = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEYS.PLAYER_ID, newId);
    return newId;
  } catch {
    return crypto.randomUUID();
  }
}
