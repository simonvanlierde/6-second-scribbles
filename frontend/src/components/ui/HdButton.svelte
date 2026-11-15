<script lang="ts">
import type { Snippet } from "svelte";
import type { HTMLButtonAttributes } from "svelte/elements";

let {
  variant = "primary",
  type = "button",
  disabled = false,
  onclick,
  children,
  ...rest
}: Props & { onclick?: (event: MouseEvent) => void; children?: Snippet } & HTMLButtonAttributes = $props();

type Variant = "primary" | "secondary" | "success" | "ghost" | "danger";

interface Props {
  variant?: Variant;
  type?: "button" | "submit";
  disabled?: boolean;
}
</script>

<button
  {...rest}
  class={[rest.class, "hd-btn", `hd-btn--${variant}`]}
  {type}
  {disabled}
  onclick={(event) => {
    onclick?.(event);
  }}
>
  {@render children?.()}
</button>

<style>
.hd-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1;
  border: var(--border-button) solid var(--color-ink);
  border-radius: var(--r-button);
  box-shadow: var(--shadow-button);
  transform: rotate(var(--rotate-button));
  cursor: pointer;
  min-height: 44px;
  min-width: 44px;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-btn:active:not(:disabled) {
  transform: rotate(var(--rotate-button)) translate(3px, 3px);
  box-shadow: 0 0 0 var(--color-ink);
}
/* Flat, dashed and muted instead of faded: opacity dropped text below 3:1, and the shape says "off" without colour. */
.hd-btn:disabled {
  background: var(--color-card);
  color: var(--color-ink-muted);
  border-style: dashed;
  box-shadow: none;
  cursor: not-allowed;
}
.hd-btn--ghost:disabled {
  background: transparent;
}
.hd-btn--primary {
  background: var(--color-primary-strong);
  color: white;
}
.hd-btn--secondary {
  background: var(--color-card);
  color: var(--color-ink);
  --rotate-button: 0.4deg;
}
.hd-btn--success {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
  --rotate-button: -0.3deg;
  border-radius: 12px 18px 14px 22px;
}
/* Destructive but quiet: outline and red text, so it does not compete with the filled primary action. */
.hd-btn--danger {
  background: var(--color-card);
  color: var(--color-primary-text);
  border-color: var(--color-primary-text);
  box-shadow: none;
  --rotate-button: 0.4deg;
}
.hd-btn--ghost {
  background: transparent;
  color: var(--color-ballpoint-blue);
  border: 0;
  box-shadow: none;
  text-decoration: underline wavy;
  text-underline-offset: 4px;
  transform: none;
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 1rem;
  padding: 8px 12px;
}
.hd-btn--ghost:active:not(:disabled) {
  transform: none;
}
</style>
