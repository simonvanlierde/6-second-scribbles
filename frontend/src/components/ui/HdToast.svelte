<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";
import { useNotifications } from "@/composables/notifications.svelte";

let { ...rest }: {} & HTMLAttributes<HTMLElement> = $props();

const toast = useNotifications();
let stack = $state<HTMLElement | null>(null);

// A manual popover lives in the top layer, where a modal <dialog>'s backdrop
// would otherwise cover the toasts. Top-layer order is last-shown-on-top, so
// raise the stack again whenever the list changes.
$effect(() => {
  void toast.notifications.length;
  if (!stack?.showPopover) return;
  if (stack.matches(":popover-open")) stack.hidePopover();
  stack.showPopover();
});
</script>

<!-- The stack owns the single live region; per-toast role="status" here would
       make each notification announce twice. -->
<div {...rest} bind:this={stack} popover="manual" class={[rest.class, "hd-toast-stack"]} role="status" aria-live="polite">
  {#each toast.notifications as n (n.id)}
    <div class={["hd-toast", `hd-toast--${n.type}`]}>{n.text}</div>
  {/each}
</div>

<style>
.hd-toast-stack {
  position: fixed;
  inset: 16px 16px auto auto;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  overflow: visible;
  width: max-content;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}
.hd-toast-stack:not(:popover-open) {
  display: none;
}
.hd-toast {
  pointer-events: auto;
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  border-radius: 14px 18px 12px 16px;
  box-shadow: var(--shadow-card);
  max-width: 320px;
}
.hd-toast--success {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
}
.hd-toast--error {
  background: var(--color-primary-strong);
  color: white;
}
.hd-toast--info {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
</style>
