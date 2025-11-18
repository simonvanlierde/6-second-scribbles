import { configDefaults, defineConfig, mergeConfig } from 'vitest/config'

import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: [
        'src/**/*.spec.{js,ts,jsx,tsx}',
        'src/**/__tests__/**/*.{js,ts}',
        'tests/*.test.{js,ts}',
        'tests/**/*.test.{js,ts}',
      ],
      setupFiles: ['./vitest.setup.ts'],
      // Keep standard excludes and skip e2e and node_modules
      exclude: [...configDefaults.exclude, 'e2e/**'],
    },
  })
)
