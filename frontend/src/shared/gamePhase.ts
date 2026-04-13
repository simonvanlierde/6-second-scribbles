import type { GamePhase } from "@/shared/types";

export function normalizeGamePhase(
	phase: string | null | undefined,
): GamePhase {
	if (
		phase === "lobby" ||
		phase === "drawing" ||
		phase === "guessing" ||
		phase === "round_results" ||
		phase === "final_results"
	) {
		return phase;
	}

	return "lobby";
}
