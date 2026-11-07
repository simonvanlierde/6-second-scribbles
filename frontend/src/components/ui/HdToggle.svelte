<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";

let {
  modelValue = $bindable(),
  label = undefined,
  help = undefined,
  onmodelValueChange,
  onchange,
  ...rest
}: Props & {
  onmodelValueChange?: (value: boolean) => void;
  onchange?: (event: Event) => void;
} & HTMLAttributes<HTMLElement> = $props();

interface Props {
  modelValue: boolean;
  label?: string;
  // Optional helper text shown as a hover/focus tooltip on an info icon.
  help?: string;
}

function onChange(event: Event) {
  modelValue = (event.target as HTMLInputElement).checked;
  onmodelValueChange?.(modelValue);
  onchange?.(event);
}
</script>

<label {...rest} class={[rest.class, "hd-toggle"]}>
  {#if label}
    <span class="hd-toggle__label">
      {label}
      {#if help}
        <span class="hd-toggle__info" role="img" title={help} aria-label={help}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4"></path>
            <path d="M12 8h.01"></path>
          </svg>
        </span>
      {/if}</span
    >
  {/if}
  <span class="hd-toggle__switch">
    <input class="hd-toggle__input" type="checkbox" checked={modelValue} aria-label={label} onchange={onChange}>
    <span class="hd-toggle__track" aria-hidden="true"></span>
  </span>
</label>

<style>
.hd-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.hd-toggle__label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-label-md);
  font-weight: 600;
  color: var(--color-ink);
}
.hd-toggle__info {
  display: inline-flex;
  color: var(--color-ink-muted);
  cursor: help;
  border-radius: var(--r-pill);
}
.hd-toggle__info svg {
  width: 14px;
  height: 14px;
}
.hd-toggle__info:focus-visible {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.hd-toggle__switch {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}
.hd-toggle__input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}
.hd-toggle__track {
  position: relative;
  display: block;
  width: 40px;
  height: 20px;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--color-ink) 28%, transparent);
  transition: background var(--motion-fast) var(--ease-out);
}
.hd-toggle__track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-card);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform var(--motion-fast) var(--ease-spring);
}
.hd-toggle__input:checked + .hd-toggle__track {
  background: var(--color-marker-red);
}
.hd-toggle__input:checked + .hd-toggle__track::after {
  transform: translateX(20px);
}
.hd-toggle__input:focus-visible + .hd-toggle__track {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
