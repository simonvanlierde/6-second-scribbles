<script lang="ts">
import { onMount } from "svelte";
import GameHeader from "@/components/game/GameHeader.svelte";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import AllDrawingsGallery from "@/components/results/AllDrawingsGallery.svelte";
import WinnerCard from "@/components/results/WinnerCard.svelte";
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useSound } from "@/composables/useSound.svelte";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();
const { play } = useSound();

let isReady = $state(false);
let leaveDialog: { request(): void } | undefined = $state();

const finalScores = $derived(store.getFinalScores());

const rankedScores = $derived.by(() => {
  const scores = finalScores;
  const ranked: Array<(typeof scores)[number] & { rank: number; isTied: boolean }> = [];

  let index = 0;
  while (index < scores.length) {
    const score = scores[index]?.score ?? 0;
    let groupEnd = index + 1;
    while (groupEnd < scores.length && scores[groupEnd]?.score === score) {
      groupEnd += 1;
    }
    const rank = index + 1;
    const isTied = groupEnd - index > 1;
    for (let i = index; i < groupEnd; i += 1) {
      const player = scores[i];
      if (!player) continue;
      ranked.push({ ...player, rank, isTied });
    }
    index = groupEnd;
  }

  return ranked;
});

const winners = $derived(rankedScores.filter((player) => player.rank === 1));
const winnerNames = $derived(formatNames(winners.map((player) => player.playerName)));
const winnerScore = $derived(winners[0]?.score ?? 0);
const winnerCards = $derived(winners.map((player) => ({ name: player.playerName, color: player.color })));

function formatNames(names: string[]) {
  if (names.length <= 1) return names[0] || t("common.unknown");
  if (names.length === 2) return `${names[0]} ${t("common.and")} ${names[1]}`;
  return names.join(", ");
}

function playAgain() {
  if (store.isHost) {
    send({ type: "restart_game" });
    store.onRestartGame();
  } else {
    isReady = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
  }
}

onMount(() => {
  play("winner");
});
</script>

  <main class="final-results">
    <GameHeader
      variant="final"
      title={t('finalResults.gameOver')}
      onleave={() => leaveDialog?.request()}
    />

    <div class="final-results__body">
      <WinnerCard name={winnerNames} winners={winnerCards} score={winnerScore} />

      <div class="final-results__columns">
        <section class="final-results__col">
          <h2 class="final-results__heading">{t("finalResults.standings")}</h2>
          <HdCard class="final-standings">
            {#each rankedScores as player (player.playerId)}<div
              class={["final-standings__row", {"final-standings__row--you": player.playerId === store.localPlayerId}]}
            >
              <span class="final-standings__rank">{player.rank}</span>
              <HdAvatar
                initial={getAvatarInitial(player.playerName)}
                color={player.color}
                size="sm"
              />
              <span class="final-standings__name">{player.playerName}</span>
              {#if player.playerId === store.localPlayerId}<HdPill class="final-standings__tag">
                {t("common.you")}
              </HdPill>
              {/if}<span class="final-standings__score">{t("common.pointsShort", { count: player.score })}</span>
            </div>{/each}
          </HdCard>

          <HdCard variant="postit" class="final-stats">
            <h3 class="final-stats__title">{t("finalResults.gameStats")}</h3>
            <dl class="final-stats__grid">
              <div class="final-stats__item">
                <dt>{t("finalResults.statRounds")}</dt>
                <dd>{store.maxRounds}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{t("finalResults.statPlayers")}</dt>
                <dd>{store.playersList.length}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{t("finalResults.statDifficulty")}</dt>
                <dd class="final-stats__difficulty">{store.difficulty}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{t("finalResults.statDrawings")}</dt>
                <dd>{store.drawingHistory.length}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{t("finalResults.statGuesses")}</dt>
                <dd>{store.totalGuessesMade}</dd>
              </div>
            </dl>
          </HdCard>
        </section>

        <section class="final-results__col"><AllDrawingsGallery drawings={store.drawingHistory} /></section>
      </div>

      <div class="final-cta">
        <HdButton class="final-cta__again" variant="primary" onclick={playAgain}>
          {store.isHost ? t("finalResults.playAgain") : isReady ? t("finalResults.readyWaiting") : t("finalResults.readyForNext")}
        </HdButton>
        <HdButton class="final-cta__home" variant="success" onclick={() => leaveDialog?.request()}>
          {t("finalResults.backHome")}
        </HdButton>
      </div>
    </div>

    <LeaveRoomDialog bind:this={leaveDialog} />
  </main>

<style>
:global(.final-results) {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-paper);
}
:global(.final-results__body) {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
:global(.final-results__columns) {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
  align-items: start;
}
:global(.final-results__col) {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
:global(.final-results__heading) {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
:global(.final-standings) {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
:global(.final-standings__row) {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--r-pill);
}
:global(.final-standings__row--you) {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
:global(.final-standings__rank) {
  min-width: 1.25rem;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary-text);
}
:global(.final-standings__name) {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-weight: 700;
}
:global(.final-standings__tag) {
  font-size: var(--text-label-sm);
}
:global(.final-standings__score) {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
/* The highlighter row stays light in dark mode, where the light text red and ink are too pale. */
:global(.final-standings__row--you) :global(.final-standings__rank),
:global(.final-standings__row--you) :global(.final-standings__score) {
  color: inherit;
}
:global(.final-stats__title) {
  margin: 0 0 var(--space-3);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
}
:global(.final-stats__grid) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: var(--space-3);
  margin: 0;
}
:global(.final-stats__item) {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
:global(.final-stats__item) dt {
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  opacity: 0.75;
}
:global(.final-stats__item) dd {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
}
:global(.final-stats__difficulty) {
  text-transform: capitalize;
}
:global(.final-cta) {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-4);
}
@media (max-width: 768px) {
  :global(.final-results__body) {
    padding: var(--space-4);
    gap: var(--space-6);
  }
  :global(.final-results__columns) {
    grid-template-columns: 1fr;
  }
  :global(.final-cta) {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
