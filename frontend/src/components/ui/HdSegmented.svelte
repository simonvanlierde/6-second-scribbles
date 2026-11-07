<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";

let {
  modelValue = $bindable(),
  options,
  name = undefined,
  ariaLabel = undefined,
  onmodelValueChange,
  ...rest
}: Props & { onmodelValueChange?: (value: string) => void } & HTMLAttributes<HTMLElement> = $props();

interface Option {
  value: string;
  label: string;
}

interface Props {
  modelValue: string;
  options: Option[];
  name?: string;
  ariaLabel?: string;
}

const generatedName = $props.id();
let groupName = $derived(name ?? generatedName);

function onChange(value: string): void {
  modelValue = value;
  onmodelValueChange?.(value);
}
</script>

<div {...rest} class={[rest.class, "hd-seg"]} role="radiogroup" aria-label={ariaLabel ?? rest["aria-label"]}>
  {#each options as opt (opt.value)}
    <label class={["hd-seg__item", { "hd-seg__item--active": opt.value === modelValue }]}>
      <input
        class="hd-seg__input"
        type="radio"
        name={groupName}
        value={opt.value}
        checked={opt.value === modelValue}
        onchange={() => {
          onChange(opt.value);
        }}
      >
      <span class="hd-seg__label">{opt.label}</span>
    </label>
  {/each}
</div>

<style>
.hd-seg {
  display: inline-flex;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  overflow: hidden;
  background: var(--color-card);
}
.hd-seg__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  min-height: 44px;
}
.hd-seg__item + .hd-seg__item {
  border-left: 1.5px solid var(--color-ink);
}
.hd-seg__input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.hd-seg__item--active {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.hd-seg__item:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
