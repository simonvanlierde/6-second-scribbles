<script setup lang="ts">
import { computed } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import { getAvatarInitial } from "@/composables/useAvatar";

const props = defineProps<{
  /** The winners' names, already joined for display. */
  name: string;
  /** Everyone sharing the top score. */
  winners: { name: string; color: string }[];
  score: number;
}>();

// A game where nobody scored has no champion, even though everyone "shares" first place.
const noWinner = computed(() => props.score <= 0 || props.winners.length === 0);
</script>

<template>
  <div v-if="noWinner" class="winner-card winner-card--none">
    <h2 class="winner-card__name">{{ $t("finalResults.noWinner") }}</h2>
    <p class="winner-card__detail">{{ $t("finalResults.noWinnerDetail") }}</p>
  </div>
  <div v-else class="winner-card">
    <span class="winner-card__ribbon" aria-hidden="true">
      {{ winners.length > 1 ? $t("finalResults.champions") : $t("finalResults.champion") }}
    </span>
    <div class="winner-card__avatars">
      <HdAvatar
        v-for="(winner, index) in winners"
        :key="index"
        :initial="getAvatarInitial(winner.name)"
        :color="winner.color"
        size="lg"
      />
    </div>
    <h2 class="winner-card__name">{{ name }}</h2>
    <p class="winner-card__score">{{ $t("common.pointsShort", { count: score }) }}</p>
  </div>
</template>

<style scoped>
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
.winner-card__avatars > * + * {
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
