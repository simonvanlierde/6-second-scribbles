import { computed, ref } from "vue";
import { z } from "zod";

import { LocaleAvailabilityItemSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";
import { type LocaleAvailability, type LocaleOption, SUPPORTED_LOCALES } from "@/shared/locales";

const availability = ref<Record<string, LocaleAvailability>>({});
const isLoading = ref(false);
const loadError = ref<string | null>(null);
const hasLoaded = ref(false);
let loaded = false;

function normalizeLocale(locale: string): string {
  return locale.toLowerCase().split("-")[0] || "en";
}

function getDisabledReason(item: LocaleAvailability | undefined): string {
  if (!item || item.category_count <= 0) {
    return "No playable categories yet";
  }

  const hasDifficultyCoverage = Object.values(item.difficulty_counts ?? {}).some((count) => count > 0);
  if (!hasDifficultyCoverage) {
    return "Missing prompt coverage across difficulties";
  }

  return "Unavailable";
}

async function fetchLocaleAvailability(force = false): Promise<void> {
  if (loaded && !force) {
    return;
  }

  isLoading.value = true;
  loadError.value = null;

  try {
    const response = await apiRequest("/api/categories/locales", {
      schema: z.array(LocaleAvailabilityItemSchema),
    });
    const normalized: Record<string, LocaleAvailability> = {};
    for (const item of response) {
      normalized[normalizeLocale(item.locale)] = item;
    }
    availability.value = normalized;
    loaded = true;
    hasLoaded.value = true;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Failed to load locale availability";
  } finally {
    isLoading.value = false;
  }
}

export function useLocaleAvailability() {
  const localeOptions = computed<LocaleOption[]>(() => {
    if (!hasLoaded.value && !loadError.value) {
      return SUPPORTED_LOCALES.map((locale) => ({ code: locale, enabled: true }));
    }

    return SUPPORTED_LOCALES.map((locale) => {
      const item = availability.value[locale];
      const enabled = !!item && item.category_count > 0;
      return {
        code: locale,
        enabled,
        reason: enabled ? undefined : getDisabledReason(item),
      };
    });
  });

  return {
    availability,
    isLoading,
    loadError,
    localeOptions,
    fetchLocaleAvailability,
  };
}
