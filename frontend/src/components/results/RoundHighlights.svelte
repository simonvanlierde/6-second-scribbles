<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { t } from "@/i18n";
import type { HighlightKind, RoundHighlight, RoundHighlights } from "@/shared/types";
import { useGameStore } from "@/stores/game.svelte";

let { highlights }: { highlights: RoundHighlights | null } = $props();

const store = useGameStore();

const ORDER: HighlightKind[] = ["bestGuesser", "speedDemon", "wildestMiss"];

let cards = $derived.by(() => {
  const h = highlights;
  if (!h) return [];
  return ORDER.map((kind) => ({ kind, data: h[kind] }))
    .filter((entry): entry is { kind: HighlightKind; data: RoundHighlight } => entry.data !== null)
    .map(({ kind, data }) => {
      const player = store.players.get(data.playerId);
      const name = player?.name ?? t("common.unknown");
      return {
        kind,
        label: t(`roundResults.${kind}`),
        detail: t(`roundResults.${kind}Detail`, { detail: data.detail }),
        name,
        initial: getAvatarInitial(name),
        color: player?.color ?? getAvatarColor(data.playerId),
      };
    });
});
</script>

<section class="highlights">
  <h2 class="highlights__title">{t("roundResults.highlightsTitle")}</h2>
  {#if cards.length}
    <div class="highlights__strip">
      {#each cards as card, index (card.kind)}
        <HdCard class="highlight" variant={index === 1 ? "postit" : "default"}>
          <HdPill class="highlight__label">{card.label}</HdPill>
          <div class="highlight__player">
            <HdAvatar initial={card.initial} color={card.color} size="md"></HdAvatar>
            <span class="highlight__name">{card.name}</span>
          </div>
          <p class="highlight__detail">{card.detail}</p>
        </HdCard>
      {/each}
    </div>
  {:else}
    <HdCard class="highlights__empty" variant="postit"> {t("roundResults.noHighlights")} </HdCard>
  {/if}
</section>

<style>
.highlights__title {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
.highlights__strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
:global(div.hd-card.highlight) {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: flex-start;
}
:global(span.hd-pill.highlight__label) {
  color: var(--color-primary-text);
  border-color: var(--color-marker-red);
  font-weight: 700;
}
.highlight__player {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.highlight__name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
  color: inherit;
}
.highlight__detail {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
}
/* The post-it stays light in dark mode, so its text keeps the card's dark ink. */
:global(.hd-card--postit) .highlight__detail {
  color: inherit;
}
:global(div.hd-card.highlights__empty) {
  text-align: center;
  font-family: var(--font-body);
}
@media (max-width: 768px) {
  .highlights__strip {
    grid-template-columns: 1fr;
  }
}
</style>
