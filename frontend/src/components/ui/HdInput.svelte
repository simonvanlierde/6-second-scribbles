<script lang="ts">
import type { HTMLInputAttributes } from "svelte/elements";

let {
  modelValue = $bindable(""),
  placeholder = "",
  variant = "default",
  type = "text",
  ariaLabel = undefined,
  onmodelValueChange,
  ...rest
}: Props & { onmodelValueChange?: (value: string) => void } & HTMLInputAttributes = $props();

let inputRef = $state<HTMLInputElement | null>(null);
export function focus() {
  inputRef?.focus();
}

type Variant = "default" | "code";

interface Props {
  modelValue?: string;
  placeholder?: string;
  variant?: Variant;
  type?: string;
  ariaLabel?: string;
}

function onInput(e: Event & { currentTarget: HTMLInputElement }): void {
  modelValue = (e.target as HTMLInputElement).value;
  onmodelValueChange?.(modelValue);
  rest.oninput?.(e);
}
</script>

<input
  {...rest}
  class={[rest.class, "hd-input", `hd-input--${variant}`]}
  bind:this={inputRef}
  value={modelValue}
  {placeholder}
  {type}
  aria-label={ariaLabel ?? rest["aria-label"]}
  oninput={onInput}
>

<style>
.hd-input {
  display: block;
  width: 100%;
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  background: var(--color-card);
  border: var(--border-input) solid var(--color-ink);
  border-radius: var(--r-input);
  box-shadow: inset 2px 2px 0 rgba(0, 0, 0, 0.04);
  min-height: 44px;
  box-sizing: border-box;
}
.hd-input::placeholder {
  color: var(--color-ink-muted);
  opacity: 0.7;
}
.hd-input--code {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  letter-spacing: 0.4em;
  text-align: center;
  text-transform: uppercase;
  border-style: dashed;
  border-radius: 14px;
}
</style>
