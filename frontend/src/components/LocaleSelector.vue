<script setup lang="ts">
import { computed } from "vue";
import { formatLocaleLabel, type LocaleOption, SUPPORTED_LOCALES } from "@/shared/locales";

const modelValue = defineModel<string>({ required: true });

const props = defineProps<{
  label?: string;
  compact?: boolean;
  help?: string;
  id?: string;
  options?: LocaleOption[];
}>();

const localeOptions = computed<LocaleOption[]>(() => {
  if (props.options?.length) {
    return props.options;
  }
  return SUPPORTED_LOCALES.map((code) => ({ code, enabled: true }));
});
</script>

<template>
  <div class="grid gap-1.5">
    <label v-if="label" class="text-sm font-bold text-ink-dark" :for="id || 'locale-selector'"> {{ label }} </label>
    <select
      :id="id || 'locale-selector'"
      class="w-full rounded-xl border border-slate-300 bg-white font-inherit"
      :class="compact ? 'min-w-44 px-2.5 py-2' : 'px-3 py-2.5'"
      :value="modelValue"
      @change="modelValue = ($event.target as HTMLSelectElement).value"
    >
      <option v-for="option in localeOptions" :key="option.code" :value="option.code" :disabled="!option.enabled">
        {{ formatLocaleLabel(option.code) }}{{ option.enabled ? "" : " (unavailable)" }}
      </option>
    </select>
    <p v-if="localeOptions.some((o) => !o.enabled)" class="m-0 text-[0.88rem] text-ink-muted">
      Unavailable locales are disabled until full playable content is ready.
    </p>
    <ul v-if="localeOptions.some((o) => !o.enabled)" class="m-0 pl-4 text-[0.82rem] text-ink-muted">
      <li v-for="option in localeOptions.filter((o) => !o.enabled)" :key="`reason-${option.code}`">
        {{ formatLocaleLabel(option.code) }}: {{ option.reason || "Unavailable" }}
      </li>
    </ul>
    <p v-if="help" class="m-0 text-[0.88rem] text-ink-muted">{{ help }}</p>
  </div>
</template>
