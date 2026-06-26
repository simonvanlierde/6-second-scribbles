import { fileURLToPath } from "node:url";
import type { UserConfig } from "vite";
import { configDefaults, defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

// Merge the project's Vite config with some test-specific overrides.
// Keep the original intent: use jsdom, respect default excludes and
// also explicitly exclude node_modules and e2e tests.
export default mergeConfig(
  viteConfig as UserConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      include: ["src/**/*.spec.{js,ts,jsx,tsx}", "src/**/__tests__/**/*.{js,ts}", "tests/**/*.test.{js,ts}"],
      setupFiles: ["./vitest.setup.ts"],
      exclude: [...configDefaults.exclude, "node_modules/**", "e2e/**"],
      root: fileURLToPath(new URL("./", import.meta.url)),
      coverage: {
        provider: "v8",
        reporter: ["text", "html", "lcov"],
        include: ["src/**"],
        exclude: [
          "src/shared/cardDecks.ts",
          "src/shared/types.ts",
          "src/main.ts",
          "src/router/index.ts",
          "src/composables/useDrawingCanvas.ts",
        ],
        thresholds: {
          lines: 60,
          functions: 60,
          branches: 50,
          statements: 60,
        },
      },
    },
  }),
);
