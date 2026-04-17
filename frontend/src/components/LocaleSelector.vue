<script setup lang="ts">
import { computed } from "vue";
import { formatLocaleLabel, type LocaleOption, SUPPORTED_LOCALES } from "@/shared/locales";

const modelValue = defineModel<string>({ required: true });

const props = defineProps<{
  label?: string;
  compact?: boolean;
  className?: string;
  help?: string;
  id?: string;
  options?: LocaleOption[];
  variant?: "default" | "pill" | "inline";
}>();

const localeOptions = computed<LocaleOption[]>(() => {
  if (props.options?.length) {
    return props.options;
  }
  return SUPPORTED_LOCALES.map((code) => ({ code, enabled: true }));
});

const isLightPill = computed(() => props.className?.includes("pill-light"));
</script>

<template>
  <div :class="variant === 'inline' ? 'inline-flex max-w-full items-center align-middle' : 'grid gap-1.5'">
    <label v-if="label" class="text-sm font-bold text-ink-dark" :for="id || 'locale-selector'"> {{ label }} </label>
    <div v-if="variant === 'pill'" class="relative inline-flex max-w-full" :class="isLightPill ? 'w-full' : ''">
      <span
        class="pointer-events-none absolute inset-y-0 left-0 flex items-center gap-2 pl-3"
        :class="isLightPill ? 'text-primary/90' : 'text-white/90'"
      >
        <span aria-hidden="true">🌐</span>
      </span>
      <select
        :id="id || 'locale-selector'"
        class="max-w-full appearance-none rounded-full outline-none transition-colors"
        :class="
          isLightPill
            ? 'h-[4.5rem] w-full border border-slate-200/95 bg-white py-3 pr-11 pl-11 text-[0.98rem] font-semibold text-slate-800 shadow-[0_6px_18px_rgba(15,23,42,0.06)] hover:border-slate-300 hover:bg-white focus:border-slate-300 focus:bg-white'
            : 'border border-white/14 bg-white/10 py-2 pr-10 pl-10 text-sm font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] backdrop-blur-sm hover:bg-white/14 focus:border-white/28 focus:bg-white/14'
        "
        :style="isLightPill ? '-webkit-text-fill-color:#1e293b;color:#1e293b;opacity:1;' : undefined"
        :value="modelValue"
        @change="modelValue = ($event.target as HTMLSelectElement).value"
      >
        <option
          v-for="option in localeOptions"
          :key="option.code"
          :value="option.code"
          :disabled="!option.enabled"
          :style="isLightPill ? 'color:#1e293b;background:#ffffff;' : undefined"
        >
          {{ formatLocaleLabel(option.code) }}{{ option.enabled ? "" : ` (${$t("common.unavailable").toLowerCase()})` }}
        </option>
      </select>
      <span
        class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
        :class="isLightPill ? 'text-slate-500' : 'text-white/70'"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M3 4.5L6 7.5L9 4.5"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    </div>
    <div
      v-else-if="variant === 'inline'"
      class="relative ml-1 inline-flex w-auto max-w-full items-center align-middle leading-none"
      data-testid="inline-locale-selector"
    >
      <select
        :id="id || 'locale-selector'"
        class="w-auto min-w-0 max-w-full appearance-none bg-transparent py-0 pr-3 text-sm leading-none font-semibold text-white/90 underline decoration-white/30 underline-offset-4 align-middle outline-none"
        :value="modelValue"
        @change="modelValue = ($event.target as HTMLSelectElement).value"
      >
        <option v-for="option in localeOptions" :key="option.code" :value="option.code" :disabled="!option.enabled">
          {{ formatLocaleLabel(option.code) }}{{ option.enabled ? "" : ` (${$t("common.unavailable").toLowerCase()})` }}
        </option>
      </select>
      <span
        class="pointer-events-none absolute top-1/2 right-0 flex -translate-y-1/2 items-center text-white/65"
        data-testid="inline-locale-chevron"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M3 4.5L6 7.5L9 4.5"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    </div>
    <select
      v-else
      :id="id || 'locale-selector'"
      class="rounded-xl border border-slate-300 bg-white font-inherit"
      :class="compact ? 'min-w-0 px-3 py-1.5 text-sm shadow-sm' : 'w-full px-3 py-2.5'"
      :value="modelValue"
      @change="modelValue = ($event.target as HTMLSelectElement).value"
    >
      <option v-for="option in localeOptions" :key="option.code" :value="option.code" :disabled="!option.enabled">
        {{ formatLocaleLabel(option.code) }}{{ option.enabled ? "" : ` (${$t("common.unavailable").toLowerCase()})` }}
      </option>
    </select>
    <p v-if="localeOptions.some((o) => !o.enabled)" class="m-0 text-[0.88rem] text-ink-muted">
      {{ $t("localeSelector.disabledHelp") }}
    </p>
    <ul v-if="localeOptions.some((o) => !o.enabled)" class="m-0 pl-4 text-[0.82rem] text-ink-muted">
      <li v-for="option in localeOptions.filter((o) => !o.enabled)" :key="`reason-${option.code}`">
        {{ $t("localeSelector.reasonUnavailable", {
            name: formatLocaleLabel(option.code),
            reason: option.reason || $t("common.unavailable"),
          }) }}
      </li>
    </ul>
    <p v-if="help" class="m-0 text-[0.88rem] text-ink-muted">{{ help }}</p>
  </div>
</template>
