<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { t } from "@/i18n";

let {
  name,
  winners,
  score,
}: {
  /** The winners' names, already joined for display. */
  name: string;
  /** Everyone sharing the top score. */
  winners: { name: string; color: string }[];
  score: number;
} = $props();

// A game where nobody scored has no champion, even though everyone "shares" first place.
let noWinner = $derived.by(() => score <= 0 || winners.length === 0);
</script>

{#if noWinner}
  <div class="winner-card winner-card--none">
    <h2 class="winner-card__name">{t("finalResults.noWinner")}</h2>
    <p class="winner-card__detail">{t("finalResults.noWinnerDetail")}</p>
  </div>
{:else}
  <div class="winner-card">
    <span class="winner-card__ribbon" aria-hidden="true">
      {winners.length > 1 ? t("finalResults.champions") : t("finalResults.champion")}
    </span>
    <div class="winner-card__avatars">
      {#each winners as winner, index (index)}
        <HdAvatar initial={getAvatarInitial(winner.name)} color={winner.color} size="lg"></HdAvatar>
      {/each}
    </div>
    <h2 class="winner-card__name">{name}</h2>
    <p class="winner-card__score">{t("common.pointsShort", { count: score })}</p>
  </div>
{/if}
<style>
.winner-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) var(--space-6) var(--space-6);
  background: linear-gradient(150deg, var(--color-highlighter-yellow), var(--color-amber));
  color: var(--color-ink-fixed);
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  transform: rotate(var(--rotate-card));
  overflow: hidden;
}
.winner-card--none {
  background: var(--color-card);
  color: var(--color-ink);
}
.winner-card__avatars {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}
/* Tied winners overlap like a stack of cards. */
.winner-card__avatars > :global(*) + :global(*) {
  margin-left: calc(-1 * var(--space-4));
}
.winner-card__detail {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  color: var(--color-ink-muted);
}
.winner-card__ribbon {
  position: absolute;
  top: var(--space-4);
  right: calc(-1 * var(--space-8));
  transform: rotate(38deg);
  padding: var(--space-1) var(--space-8);
  background: var(--color-primary-strong);
  color: white;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-label-md);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  box-shadow: var(--shadow-pill);
}
.winner-card__name {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-display-sm);
  text-align: center;
}
.winner-card__score {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
}
</style>
