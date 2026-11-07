<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";

let { initial, color, size = "md", disconnected = false, ...rest }: Props & HTMLAttributes<HTMLElement> = $props();

type Size = "sm" | "md" | "lg";

interface Props {
  initial: string;
  color: string;
  size?: Size;
  disconnected?: boolean;
}

// Apply the color through the CSSOM so the CSP can reject literal inline styles.
</script>

<span
  {...rest}
  class={[rest.class, "hd-avatar", [`hd-avatar--${size}`, { "hd-avatar--disconnected": disconnected }]]}
  style:background={color}
  aria-hidden="true"
>
  {initial}
</span>

<style>
.hd-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-avatar);
  box-shadow: var(--shadow-avatar);
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink-fixed);
  flex-shrink: 0;
}
.hd-avatar--disconnected {
  filter: grayscale(1);
  opacity: 0.45;
}
.hd-avatar--sm {
  width: 28px;
  height: 28px;
  font-size: 0.8rem;
}
.hd-avatar--md {
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
}
.hd-avatar--lg {
  width: 64px;
  height: 64px;
  font-size: 1.6rem;
  border-radius: 22px 28px 18px 24px;
  box-shadow: 4px 4px 0 var(--color-ink);
}
@supports (user-select: none) {
  .hd-avatar {
    user-select: none;
  }
}
</style>
