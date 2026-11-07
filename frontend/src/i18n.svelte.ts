import { type Messages, setupI18n, type Values } from "@lingui/core";
import { messages } from "./locales/en.json?lingui";
import { SUPPORTED_LOCALES } from "./shared/locales";

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];
export const i18n = setupI18n({ locale: "en", messages: { en: messages } });
const state = $state({ locale: "en" as AppLocale });
const loaded = new Set<AppLocale>(["en"]);
const localeLoaders = import.meta.glob<{ messages: Messages }>(["./locales/*.json", "!./locales/en.json"], {
  query: "?lingui",
});
let requestedLocale: AppLocale = "en";

export function t(key: string, values?: Values | number): string {
  // Reading the active locale lets Svelte update translated text after activation.
  void state.locale;
  return i18n._(key, typeof values === "number" ? { count: values } : values);
}

export async function setLocale(code: string): Promise<void> {
  if (!(SUPPORTED_LOCALES as readonly string[]).includes(code)) return;
  const locale = code as AppLocale;
  requestedLocale = locale;
  if (!loaded.has(locale)) {
    const catalog = await localeLoaders[`./locales/${locale}.json`]?.();
    if (!catalog) return;
    i18n.load(locale, catalog.messages);
    loaded.add(locale);
  }
  if (requestedLocale !== locale) return;
  i18n.activate(locale);
  state.locale = locale;
  document.documentElement.lang = locale;
}
