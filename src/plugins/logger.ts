import type { App } from 'vue'

import logger from '@/utils/logger'

export default {
  install(app: App) {
    // Expose the unified logger as $logger and via provide/inject
    // Components can access it with this.$logger
    // Composables/stores still import from '@/utils/logger'
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    app.config.globalProperties.$logger = logger
    app.provide('logger', logger)
  // If the logger exposes a raw consola instance, also make it available as $consola
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  if (logger.__raw) app.config.globalProperties.$consola = logger.__raw
  },
}
