<script lang="ts">
import { type Snippet, untrack } from "svelte";
import type { HTMLDialogAttributes } from "svelte/elements";
import HdButton from "@/components/ui/HdButton.svelte";
import HdIconButton from "@/components/ui/HdIconButton.svelte";

let {
  title,
  message = "",
  confirmLabel = "Confirm",
  cancelLabel,
  variant = "danger",
  closeLabel,
  actions = true,
  open = $bindable(false),
  onconfirm,
  oncancel,
  children,
  ...rest
}: Props & {
  open?: boolean;
  onconfirm?: () => void;
  oncancel?: () => void;
  children?: Snippet;
} & HTMLDialogAttributes = $props();

interface Props {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
  /** Shows a close button next to the title, which cancels like Escape does. */
  closeLabel?: string;
  /** Set false for a dialog closed only by its close button. */
  actions?: boolean;
}

let dialogRef = $state<HTMLDialogElement | null>(null);
const titleId = $props.id();
const messageId = `${titleId}-message`;

// Native <dialog> fires a `close` event on ANY close, including our own
// el.close(). Without this flag a programmatic close (confirm/backdrop) would
// re-enter onClose and emit a spurious `cancel` alongside the real event.
let programmaticClose = false;

$effect(() => {
  const value = open;
  untrack(() => {
    const isOpen = value;
    const el = dialogRef;
    if (!el) return;
    if (isOpen && !el.open) el.showModal();
    else if (!isOpen && el.open) {
      programmaticClose = true;
      el.close();
    }
  });
});

function onConfirm(): void {
  open = false;
  onconfirm?.();
}

function onCancel(): void {
  open = false;
  oncancel?.();
}

// Only user-initiated closes (Esc key) should count as a cancel; the close
// event from our own el.close() is swallowed via the programmaticClose flag.
function onClose(): void {
  if (programmaticClose) {
    programmaticClose = false;
    return;
  }
  onCancel();
}
</script>

<!-- biome-ignore lint/a11y/useKeyWithClickEvents: keyboard users cancel via Escape, handled by @close -->
<dialog
  {...rest}
  class={[rest.class, "hd-dialog"]}
  bind:this={dialogRef}
  aria-modal="true"
  aria-labelledby={titleId}
  aria-describedby={message ? messageId : undefined}
  onclick={(event) => {
    if (event.target === event.currentTarget) onCancel();
  }}
  onclose={onClose}
>
  <div class="hd-dialog__header">
    <h2 class="hd-dialog__title" id={titleId}>{title}</h2>
    {#if closeLabel}
      <HdIconButton label={closeLabel} variant="ghost" data-testid="hd-dialog-close" onclick={onCancel}>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </HdIconButton>
    {/if}
  </div>
  {#if message}
    <p class="hd-dialog__message" id={messageId}>{message}</p>
  {/if}
  {@render children?.()}
  {#if actions}
    <div class="hd-dialog__actions">
      {#if cancelLabel}
        <HdButton variant="secondary" data-testid="hd-dialog-cancel" onclick={onCancel}>
          {cancelLabel}
        </HdButton>
      {/if}
      <HdButton
        variant={variant === "danger" ? "primary" : "success"}
        data-testid="hd-dialog-confirm"
        onclick={onConfirm}
      >
        {confirmLabel}
      </HdButton>
    </div>
  {/if}
</dialog>

<style>
.hd-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  padding: 24px;
  margin: 0;
  max-width: 420px;
  width: calc(100% - 32px);
}
.hd-dialog::backdrop {
  background: rgba(0, 0, 0, 0.45);
}
.hd-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.hd-dialog__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
}
.hd-dialog__message {
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  margin: 0 0 20px;
  color: var(--color-ink-muted);
}
.hd-dialog__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
@supports (backdrop-filter: blur(2px)) {
  .hd-dialog::backdrop {
    backdrop-filter: blur(2px);
  }
}
</style>
