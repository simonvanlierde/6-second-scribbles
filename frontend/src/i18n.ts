// cspell:ignore gracz gracze graczy
import { createI18n } from "vue-i18n";
import en from "./locales/en.json";
import { SUPPORTED_LOCALES } from "./shared/locales";

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

// vue-i18n's default picks between two forms (1 / other). Polish has three:
// "1 gracz", "2-4 gracze" (also 22-24, not 12-14) and "5 graczy"; pl.json lists them in that order.
const polishForms = new Intl.PluralRules("pl");
function polishPlural(choice: number, choicesLength: number): number {
  const form = polishForms.select(Math.abs(choice));
  if (choicesLength < 3) return form === "one" ? 0 : 1;
  return form === "one" ? 0 : form === "few" ? 1 : 2;
}

// French counts zero in the singular too: "0 joueur", "1 joueur", "2 joueurs".
// (Brazilian Portuguese keeps the default: "0 jogadores".)
function frenchPlural(choice: number): number {
  return Math.abs(choice) < 2 ? 0 : 1;
}

export const i18n = createI18n({
  legacy: false,
  locale: "en" satisfies AppLocale,
  fallbackLocale: "en" satisfies AppLocale,
  messages: { en } as Record<AppLocale, typeof en>,
  pluralRules: { pl: polishPlural, fr: frenchPlural },
});

const loaded = new Set<AppLocale>(["en"]);

function isSupportedLocale(code: string): code is AppLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(code);
}

const localeLoaders = import.meta.glob<{ default: typeof en }>(["./locales/*.json", "!./locales/en.json"]);

async function loadLocale(code: AppLocale): Promise<void> {
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
  // index.html ships lang="en"; screen readers pick voice and pronunciation from it.
  document.documentElement.lang = code;
}
