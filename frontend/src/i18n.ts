import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import es from './locales/es.json'
import fr from './locales/fr.json'
import de from './locales/de.json'
import it from './locales/it.json'
import nl from './locales/nl.json'
import pt from './locales/pt.json'
import pl from './locales/pl.json'
import zhCN from './locales/zh-CN.json'
import zhTW from './locales/zh-TW.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'

export const i18n = createI18n({
  legacy: false, // Set to false to use Composition API
  locale: 'en', // Set default locale
  fallbackLocale: 'en',
  messages: {
    en,
    es,
    fr,
    de,
    it,
    nl,
    pt,
    pl,
    'zh-CN': zhCN,
    'zh-TW': zhTW,
    ja,
    ko
  }
})
