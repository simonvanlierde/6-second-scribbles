import pluginVitest from '@vitest/eslint-plugin'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import {
  configureVueProject,
  defineConfigWithVueTs,
  vueTsConfigs,
} from '@vue/eslint-config-typescript'
import pluginImport from 'eslint-plugin-import'
import pluginOxlint from 'eslint-plugin-oxlint'
import globals from 'globals'

// This is still good practice
configureVueProject({ scriptLangs: ['ts', 'tsx'] })

export default defineConfigWithVueTs(
  // Global ignores
  {
    ignores: [
      '**/dist/**',
      '**/dist-ssr/**',
      '**/coverage/**',
      '**/.partykit/**',
      '**/server/**',
    ],
  },

  // 1. Base configs
  vueTsConfigs.recommended, // This provides Vue + TS defaults, parsers, and plugins
  ...pluginOxlint.configs['flat/recommended'], // Oxlint's base rules

  // 2. Your custom rules and plugins
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      import: pluginImport,
    },
    settings: {
      'import/resolver': {
        typescript: {},
      },
    },
    rules: {
      // General JS rules
      'prefer-const': 'warn',
      'no-var': 'error',
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',

      // TS rule overrides
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-module-boundary-types': 'off',

      // Import ordering
      'import/no-unresolved': 'error',
      'import/order': [
        'warn',
        {
          groups: [
            ['builtin', 'external'],
            'internal',
            ['parent', 'sibling', 'index'],
          ],
          'newlines-between': 'always',
        },
      ],
    },
  },

  // 3. Specific overrides
  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  {
    files: ['server/**', 'server/**/*.*'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    rules: {
      'no-console': 'off',
    },
  },

  // 4. Prettier (must be last to turn off formatting rules)
  skipFormatting,
)
