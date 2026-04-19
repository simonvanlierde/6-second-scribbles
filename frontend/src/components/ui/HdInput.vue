<script setup lang="ts">
type Variant = "default" | "code";

interface Props {
  modelValue?: string;
  placeholder?: string;
  variant?: Variant;
  type?: string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  placeholder: "",
  variant: "default",
  type: "text",
  ariaLabel: undefined,
});

const emit = defineEmits<{ "update:modelValue": [string] }>();

function onInput(e: Event): void {
  emit("update:modelValue", (e.target as HTMLInputElement).value);
}
</script>

<template>
  <input
    :value="props.modelValue"
    :placeholder="props.placeholder"
    :type="props.type"
    :aria-label="props.ariaLabel"
    class="hd-input"
    :class="`hd-input--${props.variant}`"
    @input="onInput"
  >
</template>

<style scoped>
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
