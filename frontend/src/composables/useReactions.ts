import { reactive } from "vue";

export const REACTION_KEYS = ["laugh", "shock", "art", "mind-blown", "think"] as const;
export type ReactionKey = (typeof REACTION_KEYS)[number];

export const REACTION_EMOJI: Record<ReactionKey, string> = {
  laugh: "😂",
  shock: "😱",
  art: "🎨",
  "mind-blown": "🤯",
  think: "🤔",
};

type Counts = Record<ReactionKey, number>;
type ReactionsState = Record<string, Counts>;

const state = reactive<ReactionsState>({});

function emptyCounts(): Counts {
  return { laugh: 0, shock: 0, art: 0, "mind-blown": 0, think: 0 };
}

export function useReactions() {
  function add(targetId: string, key: ReactionKey): void {
    if (!state[targetId]) state[targetId] = emptyCounts();
    state[targetId][key] += 1;
  }

  function countsFor(targetId: string): Counts {
    return state[targetId] ?? emptyCounts();
  }

  function clear(): void {
    for (const k of Object.keys(state)) delete state[k];
  }

  return { add, countsFor, clear };
}
