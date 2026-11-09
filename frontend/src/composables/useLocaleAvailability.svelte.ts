import { z } from "zod";

import { LocaleAvailabilityItemSchema } from "@/generated/api";
import { t } from "@/i18n";
import { apiRequest } from "@/lib/api";
import { type LocaleAvailability, type LocaleOption, SUPPORTED_LOCALES } from "@/shared/locales";

let availability = $state<Record<string, LocaleAvailability>>({});
let isLoading = $state(false);
let loadError = $state<string | null>(null);
let hasLoaded = $state(false);

function normalizeLocale(locale: string): string {
  const [language, region] = locale.trim().replace("_", "-").split("-");
  if (!language) return "en";
  return region ? `${language.toLowerCase()}-${region.toUpperCase()}` : language.toLowerCase();
}

function getDisabledReason(item: LocaleAvailability | undefined): string {
  if (!item || item.category_count <= 0) {
    return t("localeSelector.noPlayableCategories");
  }

  const hasDifficultyCoverage = Object.values(item.difficulty_counts ?? {}).some((count) => count > 0);
  if (!hasDifficultyCoverage) {
    return t("localeSelector.missingPromptCoverage");
  }

  return t("common.unavailable");
}

async function fetchLocaleAvailability(force = false): Promise<void> {
  if (hasLoaded && !force) {
    return;
  }

  isLoading = true;
  loadError = null;

  try {
    const response = await apiRequest("/api/categories/locales", {
      schema: z.array(LocaleAvailabilityItemSchema),
    });
    const normalized: Record<string, LocaleAvailability> = {};
    for (const item of response) {
      normalized[normalizeLocale(item.locale)] = item;
    }
    availability = normalized;
    hasLoaded = true;
  } catch (error) {
    loadError = error instanceof Error ? error.message : t("localeSelector.failedToLoad");
  } finally {
    isLoading = false;
  }
}

export function useLocaleAvailability() {
  let localeOptions = $derived.by<LocaleOption[]>(() => {
    if (!(hasLoaded || loadError)) {
      return SUPPORTED_LOCALES.map((locale) => ({
        code: locale,
        enabled: true,
      }));
    }

    return SUPPORTED_LOCALES.map((locale) => {
      const item = availability[locale];
      const enabled = !!item && item.category_count > 0;
      return {
        code: locale,
        enabled,
        reason: enabled ? undefined : getDisabledReason(item),
      };
    });
  });

  return {
    get availability() {
      return availability;
    },
    set availability(value) {
      availability = value;
    },
    get isLoading() {
      return isLoading;
    },
    set isLoading(value) {
      isLoading = value;
    },
    get loadError() {
      return loadError;
    },
    set loadError(value) {
      loadError = value;
    },
    get localeOptions() {
      return localeOptions;
    },
    fetchLocaleAvailability,
  };
}
