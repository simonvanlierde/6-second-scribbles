import { type InjectionKey, inject, type ShallowRef } from "vue";

import type { useGameEngine } from "./useGameEngine";

/**
 * Typed injection key for the host's game engine instance.
 * Provided by App.vue as a ShallowRef so any child can read or replace it.
 * Value is null when no game is active or the local player is not the host.
 */
export const gameEngineKey: InjectionKey<ShallowRef<ReturnType<typeof useGameEngine> | null>> = Symbol("gameEngine");

export function injectGameEngine() {
  const gameEngineRef = inject(gameEngineKey, null);

  if (!gameEngineRef) {
    throw new Error("Game engine injection is missing.");
  }

  return gameEngineRef;
}
