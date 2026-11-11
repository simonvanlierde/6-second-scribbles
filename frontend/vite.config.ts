import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import { lingui } from "@lingui/vite-plugin";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import linguiForSvelte from "lingui-for-svelte/unplugin/vite";
import { defineConfig, type Plugin } from "vite";

// https://vite.dev/config/
// Platforms cache a preview by image URL, so the card URL carries the PNG's hash.
const ogVersion = createHash("sha256").update(readFileSync("public/og.png")).digest("hex").slice(0, 8);
const ogCardVersion: Plugin = {
  name: "og-card-version",
  transformIndexHtml: (html: string) => html.replace('/og.png"', `/og.png?v=${ogVersion}"`),
};

export default defineConfig({
  plugins: [
    linguiForSvelte(),
    svelte({ configFile: fileURLToPath(new URL("./svelte.config.js", import.meta.url)) }),
    lingui({ cwd: fileURLToPath(new URL(".", import.meta.url)) }),
    tailwindcss(),
    ogCardVersion,
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "localhost",
    port: 3001,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        codeSplitting: {
          // src/lib/zodConfig.ts must run before any schema is defined. Sharing
          // zod's chunk guarantees that; in the entry chunk it would run after
          // the shared chunk that defines the schemas.
          groups: [{ name: "zod", test: /node_modules[\\/]zod[\\/]|src[\\/]lib[\\/]zodConfig\.ts$/ }],
        },
      },
    },
  },
});
