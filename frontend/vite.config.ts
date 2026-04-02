import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import { defineConfig, type PluginOption, type UserConfig } from "vite";
import vueDevTools from "vite-plugin-vue-devtools";

const plugins: NonNullable<UserConfig["plugins"]> = [
  vue() as unknown as PluginOption,
  vueJsx() as unknown as PluginOption,
  vueDevTools() as unknown as PluginOption,
];

// https://vite.dev/config/
export default defineConfig({
  plugins,
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 3001,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
