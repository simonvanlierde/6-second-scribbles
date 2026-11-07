import { formatter } from "@lingui/format-json";
import { defineConfig } from "lingui-for-svelte/config";
import { svelteExtractor } from "lingui-for-svelte/extractor";
import { SUPPORTED_LOCALES } from "./src/shared/locales";

export default defineConfig({
  locales: [...SUPPORTED_LOCALES],
  sourceLocale: "en",
  catalogs: [{ path: "src/locales/{locale}", include: ["src"] }],
  format: formatter({ style: "minimal" }),
  extractors: [svelteExtractor],
});
