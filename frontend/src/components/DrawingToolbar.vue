<script setup lang="ts">
import { useI18n } from "vue-i18n";

import HdIconButton from "@/components/ui/HdIconButton.vue";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";

withDefaults(
  defineProps<{
    currentColor: string;
    currentWidth: number;
    palette?: readonly string[];
    sizes?: readonly number[];
    showUndo?: boolean;
    compact?: boolean;
  }>(),
  {
    palette: () => DRAW_PALETTE,
    sizes: () => BRUSH_SIZES,
    showUndo: true,
    compact: false,
  },
);

defineEmits<{
  "select-color": [string];
  "select-size": [number];
  undo: [];
  clear: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="toolbar" :class="{ 'toolbar--compact': compact }">
    <div class="toolbar__group" role="group" :aria-label="t('drawing.color')">
      <button
        v-for="color in palette"
        :key="color"
        type="button"
        class="swatch"
        :class="{ 'swatch--active': currentColor === color }"
        :style="{ background: color }"
        :aria-label="color"
        :aria-pressed="currentColor === color"
        @click="$emit('select-color', color)"
      />
    </div>
    <span class="toolbar__divider" aria-hidden="true" />
    <div class="toolbar__group" role="group" :aria-label="t('drawing.size')">
      <button
        v-for="size in sizes"
        :key="size"
        type="button"
        class="brush"
        :class="{ 'brush--active': currentWidth === size }"
        :aria-label="`${size}`"
        :aria-pressed="currentWidth === size"
        @click="$emit('select-size', size)"
      >
        <span class="brush__dot" :style="{ width: `${size + 4}px`, height: `${size + 4}px` }" />
      </button>
    </div>
    <div class="toolbar__group toolbar__group--end">
      <HdIconButton v-if="showUndo" class="toolbar__icon-btn" :label="t('drawing.undo')" @click="$emit('undo')">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M3 7v6h6" />
          <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
        </svg>
      </HdIconButton>
      <HdIconButton class="toolbar__icon-btn" :label="t('drawing.clear')" @click="$emit('clear')">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M3 6h18" />
          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14" />
        </svg>
      </HdIconButton>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.toolbar__group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.toolbar__group--end {
  margin-left: auto;
  gap: var(--space-1);
}
.toolbar__divider {
  align-self: stretch;
  width: 2px;
  margin: 4px 0;
  background: color-mix(in srgb, var(--color-ink) 18%, transparent);
  border-radius: var(--r-pill);
}
.swatch {
  width: 44px;
  height: 44px;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  cursor: pointer;
  padding: 0;
  transition: transform var(--motion-fast) var(--ease-spring);
}
.swatch--active {
  transform: scale(1.15) rotate(-3deg);
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.brush {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  cursor: pointer;
  padding: 0;
}
.brush--active {
  background: var(--color-highlighter-yellow);
}
.brush__dot {
  display: inline-block;
  background: var(--color-ink);
  border-radius: 50%;
}

/* Compact variant for the lobby's smaller doodle pad — keeps colors + sizes +
   clear on a single row in the narrower card. */
.toolbar--compact {
  gap: var(--space-2);
}
.toolbar--compact .toolbar__group {
  gap: var(--space-1);
}
.toolbar--compact .swatch,
.toolbar--compact .brush,
.toolbar--compact .toolbar__icon-btn {
  width: 38px;
  height: 38px;
}
</style>
