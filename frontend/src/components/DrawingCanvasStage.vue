<script setup lang="ts">
// Theme-aware canvas backdrop shared by the in-game and lobby drawing pads: a faint
// dot grid on the card surface, with the <canvas> passed in via slot so each
// consumer keeps its own template ref + useDrawingCanvas wiring.
</script>

<template>
  <div class="canvas-stage"><slot /></div>
</template>

<style scoped>
.canvas-stage {
  position: relative;
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  background-color: var(--color-card);
  /* Faint 20px dot grid for paper feel. */
  background-image: radial-gradient(color-mix(in srgb, var(--color-ink) 16%, transparent) 1px, transparent 1px);
  background-size: 20px 20px;
  overflow: hidden;
}
.canvas-stage :slotted(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
}
</style>
