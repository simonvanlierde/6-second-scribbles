import type { LocaleAvailabilityItem } from "@/generated/api";

export const SUPPORTED_LOCALES = ["en", "es", "fr"] as const;

export type LocaleAvailability = LocaleAvailabilityItem;

export type LocaleOption = {
  code: string;
  enabled: boolean;
  reason?: string;
};

export const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
};

export function formatLocaleLabel(locale: string): string {
  return LOCALE_LABELS[locale] || locale;
}
