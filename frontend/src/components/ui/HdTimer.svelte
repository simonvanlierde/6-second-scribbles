<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";

let { seconds, urgentAt = 10, ...rest }: Props & HTMLAttributes<HTMLElement> = $props();

interface Props {
  seconds: number;
  urgentAt?: number;
}

let isUrgent = $derived.by(() => seconds <= urgentAt);
</script>

<div {...rest} class={[rest.class, "hd-timer", isUrgent ? "hd-timer--urgent" : "hd-timer--calm"]} aria-hidden="true">
  <!-- aria-hidden: a per-second live region would make screen readers announce
         every tick. The countdown is a visual urgency cue only. -->
  {seconds}
</div>

<style>
.hd-timer {
  display: inline-block;
  padding: 6px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 2.4rem;
  line-height: 1.05;
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-button);
  box-shadow: var(--shadow-card);
  min-width: 4rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
  transform: rotate(-1deg);
  transition:
    background-color var(--motion-fast) var(--ease-out),
    color var(--motion-fast) var(--ease-out);
}
.hd-timer--calm {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.hd-timer--urgent {
  background: var(--color-primary-strong);
  color: white;
  animation: heartbeat 1s var(--ease-spring) infinite;
}
@keyframes heartbeat {
  0%,
  100% {
    transform: rotate(-1deg) scale(1);
  }
  50% {
    transform: rotate(-1deg) scale(1.04);
  }
}
@media (prefers-reduced-motion: reduce) {
  .hd-timer--urgent {
    animation: none;
  }
}
</style>
