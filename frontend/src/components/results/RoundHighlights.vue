<script setup lang="ts">
import { computed } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { i18n } from "@/i18n";
import type { HighlightKind, RoundHighlight, RoundHighlights } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const props = defineProps<{ highlights: RoundHighlights | null }>();

const store = useGameStore();

const ORDER: HighlightKind[] = ["bestGuesser", "speedDemon", "wildestMiss"];

const cards = computed(() => {
  const h = props.highlights;
  if (!h) return [];
  return ORDER.map((kind) => ({ kind, data: h[kind] }))
    .filter((entry): entry is { kind: HighlightKind; data: RoundHighlight } => entry.data !== null)
    .map(({ kind, data }) => {
      const player = store.players.get(data.playerId);
      const name = player?.name ?? i18n.global.t("common.unknown");
      return {
        kind,
        label: i18n.global.t(`roundResults.${kind}`),
        detail: i18n.global.t(`roundResults.${kind}Detail`, { detail: data.detail }),
        name,
        initial: getAvatarInitial(name),
        color: player?.color ?? getAvatarColor(data.playerId),
      };
    });
});
</script>

<template>
  <section class="highlights">
    <h2 class="highlights__title">{{ $t("roundResults.highlightsTitle") }}</h2>
    <div v-if="cards.length" class="highlights__strip">
      <HdCard
        v-for="(card, index) in cards"
        :key="card.kind"
        :variant="index === 1 ? 'postit' : 'default'"
        class="highlight"
      >
        <HdPill class="highlight__label">{{ card.label }}</HdPill>
        <div class="highlight__player">
          <HdAvatar :initial="card.initial" :color="card.color" size="md" />
          <span class="highlight__name">{{ card.name }}</span>
        </div>
        <p class="highlight__detail">{{ card.detail }}</p>
      </HdCard>
    </div>
    <HdCard v-else variant="postit" class="highlights__empty"> {{ $t("roundResults.noHighlights") }} </HdCard>
  </section>
</template>

<style scoped>
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
.highlight {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: flex-start;
}
.highlight__label {
  color: var(--color-marker-red);
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
  color: var(--color-ink);
}
.highlight__detail {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
}
.highlights__empty {
  text-align: center;
  font-family: var(--font-body);
}
@media (max-width: 768px) {
  .highlights__strip {
    grid-template-columns: 1fr;
  }
}
</style>
