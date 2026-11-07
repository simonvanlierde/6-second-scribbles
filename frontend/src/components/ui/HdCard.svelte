<script lang="ts">
import type { Snippet } from "svelte";
import type { HTMLAttributes } from "svelte/elements";

let { variant = "default", children, ...rest }: Props & { children?: Snippet } & HTMLAttributes<HTMLElement> = $props();

type Variant = "default" | "postit";

interface Props {
  variant?: Variant;
}
</script>

<div {...rest} class={[rest.class, "hd-card", `hd-card--${variant}`]}>{@render children?.()}</div>

<style>
.hd-card {
  padding: var(--space-4);
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  transform: rotate(var(--rotate-card));
}
.hd-card--default {
  background: var(--color-card);
}
.hd-card--postit {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
  --rotate-card: var(--rotate-postit);
  border-width: 1px;
  border-color: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  box-shadow: 2px 4px 6px rgba(0, 0, 0, 0.16);
  font-size: 0.95rem;
}
</style>
