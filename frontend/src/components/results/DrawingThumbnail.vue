<script setup lang="ts">
import { ref, watch } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import { getAvatarInitial } from "@/composables/useAvatar";

const props = defineProps<{
  drawing?: string;
  name: string;
  color: string;
  alt: string;
}>();

const broken = ref(false);

// The instance is reused across rounds (keyed by player id), so clear a stale
// error when a new drawing arrives — otherwise one failed load pins the
// placeholder for the rest of the game.
watch(
  () => props.drawing,
  () => {
    broken.value = false;
  },
);
</script>

<template>
  <figure class="thumb">
    <HdAvatar class="thumb__avatar" :initial="getAvatarInitial(name)" :color="color" size="sm" />
    <div class="thumb__stage">
      <img v-if="drawing && !broken" :src="drawing" :alt="alt" class="thumb__img" @error="broken = true">
      <span v-else class="thumb__placeholder" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 16l5-5 4 4 3-3 6 6" />
        </svg>
      </span>
      <slot name="overlay" />
    </div>
    <figcaption class="thumb__name">{{ name }}</figcaption>
  </figure>
</template>

<style scoped>
.thumb {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
}
.thumb__avatar {
  position: absolute;
  top: calc(-1 * var(--space-2));
  left: calc(-1 * var(--space-2));
  z-index: 2;
}
.thumb__stage {
  position: relative;
  aspect-ratio: 4 / 3;
  background: var(--color-paper);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.thumb__placeholder {
  color: var(--color-ink-muted);
  width: 36px;
  height: 36px;
}
.thumb__placeholder svg {
  width: 100%;
  height: 100%;
}
.thumb__name {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  font-weight: 700;
  text-align: center;
  color: var(--color-ink);
}
</style>
