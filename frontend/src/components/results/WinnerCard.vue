<script setup lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.vue";

defineProps<{
  name: string;
  initial: string;
  color: string;
  score: number;
  isTie: boolean;
}>();
</script>

<template>
  <div class="winner-card">
    <span class="winner-card__ribbon" aria-hidden="true">
      {{ isTie ? $t("finalResults.champions") : $t("finalResults.champion") }}
    </span>
    <HdAvatar :initial="initial" :color="color" size="lg" />
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
.winner-card__ribbon {
  position: absolute;
  top: var(--space-4);
  right: calc(-1 * var(--space-8));
  transform: rotate(38deg);
  padding: var(--space-1) var(--space-8);
  background: var(--color-marker-red);
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
