<script lang="ts">
import type { Snippet } from "svelte";
import type { HTMLButtonAttributes } from "svelte/elements";

let {
  label,
  title = undefined,
  variant = "default",
  disabled = false,
  onclick,
  children,
  ...rest
}: Props & { onclick?: (event: MouseEvent) => void; children?: Snippet } & HTMLButtonAttributes = $props();

type Variant = "default" | "ghost";

interface Props {
  label: string;
  // Optional hover tooltip; falls back to `label` when omitted.
  title?: string;
  variant?: Variant;
  disabled?: boolean;
}
</script>

<button
  {...rest}
  class={[rest.class, "hd-icon-btn", `hd-icon-btn--${variant}`]}
  type="button"
  aria-label={label}
  title={title ?? label}
  {disabled}
  onclick={(event) => {
    onclick?.(event);
  }}
>
  {@render children?.()}
</button>

<style>
.hd-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--r-pill);
  cursor: pointer;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-icon-btn--default {
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  box-shadow: var(--shadow-pill);
  transform: rotate(-1deg);
}
.hd-icon-btn--default:active:not(:disabled) {
  transform: rotate(-1deg) translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
.hd-icon-btn--ghost {
  background: transparent;
  color: var(--color-ink);
  border: 0;
  box-shadow: none;
}
.hd-icon-btn--ghost:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-ink) 8%, transparent);
}
.hd-icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.hd-icon-btn :global(svg) {
  width: 20px;
  height: 20px;
}
</style>
