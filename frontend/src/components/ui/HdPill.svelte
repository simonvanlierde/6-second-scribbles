<script lang="ts">
import type { Snippet } from "svelte";
import type { HTMLAttributes } from "svelte/elements";

let { variant = "default", children, ...rest }: Props & { children?: Snippet } & HTMLAttributes<HTMLElement> = $props();

type Variant = "default" | "info" | "success";

interface Props {
  variant?: Variant;
}
</script>

<span {...rest} class={[rest.class, "hd-pill", `hd-pill--${variant}`]}> {@render children?.()} </span>

<style>
.hd-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
  background: var(--color-card);
  box-shadow: var(--shadow-pill);
  line-height: 1.4;
}
.hd-pill--default {
  color: var(--color-ink);
}
.hd-pill--info {
  color: var(--color-ballpoint-blue);
  border-color: var(--color-ballpoint-blue);
}
.hd-pill--success {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
}
</style>
