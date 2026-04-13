<script setup lang="ts">
import {
    formatLocaleLabel,
    SUPPORTED_LOCALES,
    type LocaleOption,
} from "@/shared/locales";
import { computed } from "vue";

const props = defineProps<{
  modelValue: string;
  label?: string;
  compact?: boolean;
  help?: string;
  id?: string;
  options?: LocaleOption[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const localeOptions = computed<LocaleOption[]>(() => {
  if (props.options?.length) {
    return props.options;
  }

  return SUPPORTED_LOCALES.map((code) => ({ code, enabled: true }));
});
</script>

<template>
  <div :class="['locale-selector', { 'locale-selector--compact': compact }]">
    <label v-if="label" class="locale-selector__label" :for="id || 'locale-selector'">{{ label }}</label>
    <select
      :id="id || 'locale-selector'"
      class="locale-selector__select"
      :value="modelValue"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-for="option in localeOptions" :key="option.code" :value="option.code" :disabled="!option.enabled">
        {{ formatLocaleLabel(option.code) }}{{ option.enabled ? "" : " (unavailable)" }}
      </option>
    </select>
    <p v-if="localeOptions.some((option) => !option.enabled)" class="locale-selector__help">
      Unavailable locales are disabled until full playable content is ready.
    </p>
    <ul v-if="localeOptions.some((option) => !option.enabled)" class="locale-selector__reasons">
      <li v-for="option in localeOptions.filter((option) => !option.enabled)" :key="`reason-${option.code}`">
        {{ formatLocaleLabel(option.code) }}: {{ option.reason || "Unavailable" }}
      </li>
    </ul>
    <p v-if="help" class="locale-selector__help">{{ help }}</p>
  </div>
</template>

<style scoped>
.locale-selector {
  display: grid;
  gap: 0.4rem;
}

.locale-selector__label {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text-dark);
}

.locale-selector__select {
  width: 100%;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  background: white;
  font: inherit;
}

.locale-selector__help {
  margin: 0;
  font-size: 0.88rem;
  color: var(--color-text-muted);
}

.locale-selector__reasons {
  margin: 0;
  padding-left: 1rem;
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.locale-selector--compact .locale-selector__select {
  min-width: 11rem;
  padding: 0.55rem 0.7rem;
}
</style>
