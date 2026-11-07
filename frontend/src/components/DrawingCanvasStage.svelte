<script lang="ts">
import type { Snippet } from "svelte";
import type { HTMLAttributes } from "svelte/elements";

let { children, ...rest }: { children?: Snippet } & HTMLAttributes<HTMLElement> = $props();

// Canvas backdrop shared by the in-game and lobby drawing pads: a faint dot grid
// on fixed light paper (the same in both themes), with the <canvas> passed in via a snippet so each
// consumer keeps its own template ref + useDrawingCanvas wiring.
</script>

<div {...rest} class={[rest.class, "canvas-stage"]}>{@render children?.()}</div>

<style>
.canvas-stage {
  position: relative;
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  background-color: var(--color-drawing-paper);
  /* Faint 20px dot grid for paper feel. */
  background-image: radial-gradient(color-mix(in srgb, var(--color-ink-fixed) 16%, transparent) 1px, transparent 1px);
  background-size: 20px 20px;
  overflow: hidden;
}
.canvas-stage :global(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
}
</style>
