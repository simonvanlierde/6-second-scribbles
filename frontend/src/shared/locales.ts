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

/**
 * Map a BCP 47 tag such as navigator.language to the app's locale codes: the
 * base language, except Chinese, which the app splits by script.
 */
export function getBrowserLocale(tag = typeof navigator === "undefined" ? "" : navigator.language): string {
  const [base, ...subtags] = (tag || "en").toLowerCase().split("-");
  if (base === "zh") {
    // Traditional script: zh-Hant, or a region that uses it by default.
    return subtags.some((s) => ["hant", "tw", "hk", "mo"].includes(s)) ? "zh-TW" : "zh-CN";
  }
  return base || "en";
}

export type LocaleAvailability = LocaleAvailabilityItem;

export type LocaleOption = {
  code: string;
  enabled: boolean;
  reason?: string;
};

const LOCALE_LABELS: Record<string, string> = {
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
  // biome-ignore lint/security/noSecrets: This is not a secret, it's just a label for a locale.
  "zh-CN": "中文（简体）",
  // biome-ignore lint/security/noSecrets: This is not a secret, it's just a label for a locale.
  "zh-TW": "中文（繁體）",
};

export function formatLocaleLabel(locale: string): string {
  return LOCALE_LABELS[locale] || locale;
}
