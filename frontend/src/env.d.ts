/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_HOST?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "*.json?lingui" {
  export const messages: import("@lingui/core").Messages;
}
