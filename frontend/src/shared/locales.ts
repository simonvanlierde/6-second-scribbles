import type { LocaleAvailabilityItem } from "@/generated/api";

export const SUPPORTED_LOCALES = [
  "en",
  "de",
  "es",
  "fr",
  "it",
  "ja",
  "ko",
  "nl",
  "pl",
  "pt",
  "zh-CN",
  "zh-TW",
] as const;

export const PLAYABLE_CONTENT_LOCALES = [
  "en",
  "de",
  "es",
  "fr",
  "it",
  "ja",
  "ko",
  "nl",
  "pl",
  "pt",
  "zh-CN",
  "zh-TW",
] as const;

export type LocaleAvailability = LocaleAvailabilityItem;

export type LocaleOption = {
  code: string;
  enabled: boolean;
  reason?: string;
};

export const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  de: "Deutsch",
  es: "Español",
  fr: "Français",
  it: "Italiano",
  ja: "日本語",
  ko: "한국어",
  nl: "Nederlands",
  pl: "Polski",
  pt: "Português",
  "zh-CN": "中文（简体）",
  "zh-TW": "中文（繁體）",
};

export function formatLocaleLabel(locale: string): string {
  return LOCALE_LABELS[locale] || locale;
}
