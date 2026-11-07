<script lang="ts">
import HdIconButton from "@/components/ui/HdIconButton.svelte";
import { BRUSH_SIZE_NAMES, BRUSH_SIZES, DRAW_COLOR_NAMES, DRAW_PALETTE } from "@/config/drawing";
import { t } from "@/i18n";

let {
  currentColor,
  currentWidth,
  palette = DRAW_PALETTE,
  sizes = BRUSH_SIZES,
  showUndo = true,
  compact = false,
  onselectColor,
  onselectSize,
  onundo,
  onclear,
}: {
  currentColor: string;
  currentWidth: number;
  palette?: readonly string[];
  sizes?: readonly number[];
  showUndo?: boolean;
  compact?: boolean;
} & {
  onselectColor?: (value: string) => void;
  onselectSize?: (value: number) => void;
  onundo?: () => void;
  onclear?: () => void;
} = $props();
</script>

<div class={["toolbar", { "toolbar--compact": compact }]}>
  <!-- biome-ignore lint/a11y/useSemanticElements: role=group + aria-label names the swatch cluster; no native element fits -->
  <div class="toolbar__group" role="group" aria-label={t("drawing.color")}>
    {#each palette as color (color)}
      <button
        class={["swatch", { "swatch--active": currentColor === color }]}
        type="button"
        style:background={color}
        aria-label={DRAW_COLOR_NAMES[color] ? t(DRAW_COLOR_NAMES[color]) : color}
        aria-pressed={currentColor === color}
        onclick={() => {
          onselectColor?.(color);
        }}
      >
        <!-- A check, not an outline: the blue outline is the keyboard focus ring. -->
        {#if currentColor === color}
          <svg
            class="swatch__check"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="4"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        {/if}
      </button>
    {/each}
  </div>
  <span class="toolbar__divider" aria-hidden="true"></span>
  <!-- biome-ignore lint/a11y/useSemanticElements: role=group + aria-label names the brush-size cluster; no native element fits -->
  <div class="toolbar__group" role="group" aria-label={t("drawing.size")}>
    {#each sizes as size (size)}
      <button
        class={["brush", { "brush--active": currentWidth === size }]}
        type="button"
        aria-label={BRUSH_SIZE_NAMES[size] ? t(BRUSH_SIZE_NAMES[size]) : `${size}`}
        aria-pressed={currentWidth === size}
        onclick={() => {
          onselectSize?.(size);
        }}
      >
        <span class="brush__dot" style:width={`${size + 4}px`} style:height={`${size + 4}px`}></span>
      </button>
    {/each}
  </div>
  <div class="toolbar__group toolbar__group--end">
    {#if showUndo}
      <HdIconButton
        class="toolbar__icon-btn"
        label={t("drawing.undo")}
        onclick={() => {
          onundo?.();
        }}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M3 7v6h6"></path>
          <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path>
        </svg>
      </HdIconButton>
    {/if}
    <HdIconButton
      class="toolbar__icon-btn"
      label={t("drawing.clear")}
      onclick={() => {
        onclear?.();
      }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M3 6h18"></path>
        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"></path>
      </svg>
    </HdIconButton>
  </div>
</div>

<style>
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
  position: relative;
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
  border-width: 3px;
}
.swatch__check {
  position: absolute;
  top: -7px;
  right: -7px;
  width: 20px;
  height: 20px;
  padding: 3px;
  border-radius: 50%;
  background: var(--color-ink);
  color: var(--color-paper);
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
/* The yellow active fill stays light in dark mode, so the dot needs fixed dark ink. */
.brush--active .brush__dot {
  background: var(--color-ink-fixed);
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
.toolbar--compact :global(button.hd-icon-btn.toolbar__icon-btn) {
  position: relative;
  width: 38px;
  height: 38px;
}
/* Grow the touch target to 44px without widening the row. */
.toolbar--compact .swatch::after,
.toolbar--compact .brush::after,
.toolbar--compact :global(button.hd-icon-btn.toolbar__icon-btn)::after {
  content: "";
  position: absolute;
  inset: -3px;
}
</style>
