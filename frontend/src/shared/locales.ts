export const SUPPORTED_LOCALES = ["en", "es", "fr"] as const;

export type LocaleAvailability = {
  locale: string;
  category_count: number;
  difficulty_counts: Record<string, number>;
};

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
