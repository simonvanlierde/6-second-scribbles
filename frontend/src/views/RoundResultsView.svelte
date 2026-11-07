<script lang="ts">
import { onDestroy, onMount } from "svelte";
import GameHeader from "@/components/game/GameHeader.svelte";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import DrawingRevealGrid from "@/components/results/DrawingRevealGrid.svelte";
import RoundHighlights from "@/components/results/RoundHighlights.svelte";
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useSound } from "@/composables/useSound.svelte";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { play } = useSound();

let countdown = $state(GAME_TIMINGS.ROUND_RESULTS_COUNTDOWN_S);
let leaveDialog: { request(): void } | undefined = $state();
let countdownInterval: number | null = null;

const currentScores = $derived([...store.playersList].sort((a, b) => b.score - a.score));

const resultsByPlayer = $derived.by(() => {
  const grouped: Record<
    string,
    { targetName: string; correctGuesses: number; totalItems: number; pointsEarned: number }[]
  > = {};

  for (const result of store.lastRoundResults) {
    const targetPlayer = store.players.get(result.targetPlayerId);
    const bucket = grouped[result.playerId] ?? [];
    bucket.push({
      targetName: targetPlayer?.name || t("common.unknown"),
      correctGuesses: result.correctGuesses,
      totalItems: result.totalItems,
      pointsEarned: result.pointsEarned,
    });
    grouped[result.playerId] = bucket;
  }

  return grouped;
});

const isLastRound = $derived(store.currentRound >= store.maxRounds);

onMount(() => {
  play("reveal");
  countdownInterval = window.setInterval(() => {
    countdown--;
    if (countdown <= 0) {
      clearInterval(countdownInterval ?? undefined);
      countdownInterval = null;
    }
  }, 1000);
});

onDestroy(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
});
</script>

  <main class="round-results">
    <GameHeader timeLeft={countdown} onleave={() => leaveDialog?.request()} />

    <div class="round-results__body">
      <div class="round-results__intro">
        <h1 class="round-results__title">{t("roundResults.title", { round: store.currentRound })}</h1>
        <p class="round-results__lead">
          {isLastRound ? t("roundResults.finalResultsSoon") : t("roundResults.nextRoundSoon")}
          {t("common.countdownIn", { count: countdown })}
        </p>
      </div>

      <RoundHighlights highlights={store.lastHighlights} />

      <div class="round-results__columns">
        <section class="round-results__col">
          <h2 class="round-results__heading">{t("roundResults.roundPerformance")}</h2>
          <div class="performance">
            {#each store.playersList as player (player.id)}<HdCard class="performance__card">
              <div class="performance__head">
                <HdAvatar
                  initial={getAvatarInitial(player.name)}
                  color={player.color}
                  size="sm"
                  disconnected={!player.connected}
                />
                <span class="performance__name">{player.name}</span>
              </div>
              {#if resultsByPlayer[player.id]}<ul class="performance__list">
                {#each resultsByPlayer[player.id] as result (result.targetName)}<li class="performance__row">
                  <span class="performance__target">
                    {t("roundResults.guessedPlayersDrawing", { name: result.targetName })}
                  </span>
                  <span class="performance__score">{result.correctGuesses}/{result.totalItems}</span>
                  <HdPill variant="success">+{t("common.pointsShort", { count: result.pointsEarned })}</HdPill>
                </li>{/each}
              </ul>
              {:else}<p class="performance__empty">{t("roundResults.noGuessesSubmitted")}</p>
            {/if}</HdCard>{/each}
          </div>
        </section>

        <section class="round-results__col">
          <h2 class="round-results__heading">{t("roundResults.currentStandings")}</h2>
          <HdCard class="standings">
            {#each currentScores as player, index (player.id)}<div
              class={["standings__row", {"standings__row--you": player.id === store.localPlayerId}]}
            >
              <span class="standings__rank">{index + 1}</span>
              <HdAvatar
                initial={getAvatarInitial(player.name)}
                color={player.color}
                size="sm"
                disconnected={!player.connected}
              />
              <span class="standings__name">{player.name}</span>
              {#if player.id === store.localPlayerId}<HdPill class="standings__you">{t("common.you")}</HdPill>
              {/if}<span class="standings__score">{t("common.pointsShort", { count: player.score })}</span>
            </div>{/each}
          </HdCard>
        </section>
      </div>

      <DrawingRevealGrid />
    </div>

    <LeaveRoomDialog bind:this={leaveDialog} />
  </main>

<style>
:global(.round-results) {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-paper);
}
:global(.round-results__body) {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
:global(.round-results__title) {
  margin: 0 0 var(--space-1);
  font-size: var(--text-heading-lg);
  color: var(--color-ink);
}
:global(.round-results__lead) {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
}
:global(.round-results__columns) {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
  align-items: start;
}
:global(.round-results__heading) {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
:global(.performance) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
:global(.performance__head) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
:global(.performance__name) {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
  color: var(--color-ink);
}
:global(.performance__list) {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
:global(.performance__row) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
:global(.performance__target) {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
}
:global(.performance__score) {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
:global(.performance__empty) {
  margin: 0;
  font-family: var(--font-body);
  font-style: italic;
  color: var(--color-ink-muted);
}
:global(.standings) {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
:global(.standings__row) {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--r-pill);
}
:global(.standings__row--you) {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
:global(.standings__rank) {
  min-width: 1.25rem;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary-text);
}
:global(.standings__name) {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-weight: 700;
}
:global(.standings__you) {
  font-size: var(--text-label-sm);
}
:global(.standings__score) {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
/* The highlighter row stays light in dark mode, where the light text red and ink are too pale. */
:global(.standings__row--you) :global(.standings__rank),
:global(.standings__row--you) :global(.standings__score) {
  color: inherit;
}
@media (max-width: 768px) {
  :global(.round-results__body) {
    padding: var(--space-4);
    gap: var(--space-6);
  }
  :global(.round-results__columns) {
    grid-template-columns: 1fr;
  }
}
</style>
