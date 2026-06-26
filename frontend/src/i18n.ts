import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import { SUPPORTED_LOCALES } from "./shared/locales";

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

export const i18n = createI18n({
  legacy: false,
  locale: "en" satisfies AppLocale,
  fallbackLocale: "en" satisfies AppLocale,
  messages: { en } as Record<AppLocale, typeof en>,
});

const loaded = new Set<AppLocale>(["en"]);

export function isSupportedLocale(code: string): code is AppLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(code);
}

const localeLoaders = import.meta.glob<{ default: typeof en }>(["./locales/*.json", "!./locales/en.json"]);

export async function loadLocale(code: AppLocale): Promise<void> {
  if (loaded.has(code)) return;
  const loader = localeLoaders[`./locales/${code}.json`];
  if (!loader) return;
  const mod = await loader();
  i18n.global.setLocaleMessage(code, mod.default);
  loaded.add(code);
}

export async function setLocale(code: string): Promise<void> {
  if (!isSupportedLocale(code)) return;
  await loadLocale(code);
  i18n.global.locale.value = code;
}
