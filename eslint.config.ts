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
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/.partykit/**', '**/server/**'],
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
      // Configure resolvers so `eslint-plugin-import` can find TypeScript paths and .vue files
      'import/resolver': {
        // Use the TypeScript resolver to read tsconfig `paths` and `baseUrl`.
        // Point it at the relevant tsconfig files so aliases like `@/*` resolve.
        typescript: {
          // Use the main app tsconfig so path aliases like `@/*` resolve cleanly.
          project: ['./tsconfig.app.json'],
          alwaysTryTypes: true,
        },
        // Fallback to Node resolver and make sure .vue files are recognized
        node: {
          extensions: ['.js', '.jsx', '.ts', '.tsx', '.vue', '.json'],
        },
      },

      // Make eslint-plugin-import aware of these extensions and map the TS parser to them
      'import/extensions': ['.js', '.jsx', '.ts', '.tsx', '.vue', '.json'],
      'import/parsers': {
        '@typescript-eslint/parser': ['.ts', '.tsx', '.vue'],
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
          groups: [['builtin', 'external'], 'internal', ['parent', 'sibling', 'index']],
          'newlines-between': 'always',
        },
      ],
    },
  },

  // 3. Specific overrides
  {
    // Apply Vitest plugin settings to all test files and folders
    ...pluginVitest.configs.recommended,
    files: [
      'src/**/*.spec.{js,ts,jsx,tsx}',
      'src/**/__tests__/**/*.{js,ts}',
      'tests/**/*.test.{js,ts}',
      'tests/**',
    ],
    // For test files, use the test tsconfig so path aliases and test types resolve
    settings: {
      'import/resolver': {
        typescript: { project: ['./tsconfig.vitest.json'], alwaysTryTypes: true },
        node: { extensions: ['.js', '.jsx', '.ts', '.tsx', '.vue', '.json'] },
      },
    },
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
  skipFormatting
)
