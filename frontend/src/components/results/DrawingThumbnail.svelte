<script lang="ts">
import { type Snippet, untrack } from "svelte";
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";

let {
  drawing,
  name,
  color,
  alt,
  children,
}: {
  drawing?: string;
  name: string;
  color: string;
  alt: string;
} & { children?: Snippet } = $props();

let broken = $state(false);

// The instance is reused across rounds (keyed by player id), so clear a stale
// error when a new drawing arrives — otherwise one failed load pins the
// placeholder for the rest of the game.
let watchStarted0 = false;
$effect(() => {
  void drawing;
  if (!watchStarted0) {
    watchStarted0 = true;
    return;
  }
  untrack(() => {
    broken = false;
  });
});
</script>

<figure class="thumb">
  <HdAvatar class="thumb__avatar" initial={getAvatarInitial(name)} {color} size="sm"></HdAvatar>
  <div class="thumb__stage">
    {#if drawing && !broken}
      <!-- biome-ignore lint/a11y/noNoninteractiveElementInteractions: onerror handles image resource failures. -->
      <img
        class="thumb__img"
        src={drawing}
        {alt}
        onerror={() => {
          broken = true;
        }}
      >
    {:else}
      <span class="thumb__placeholder" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
          <path d="M3 16l5-5 4 4 3-3 6 6"></path>
        </svg>
      </span>
    {/if}
    {@render children?.()}
  </div>
  <figcaption class="thumb__name">{name}</figcaption>
</figure>

<style>
.thumb {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
}
:global(span.hd-avatar.thumb__avatar) {
  position: absolute;
  top: calc(-1 * var(--space-2));
  left: calc(-1 * var(--space-2));
  z-index: 2;
}
.thumb__stage {
  position: relative;
  aspect-ratio: 4 / 3;
  background: var(--color-drawing-paper);
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
