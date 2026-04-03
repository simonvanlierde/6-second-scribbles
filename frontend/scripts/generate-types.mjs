#!/usr/bin/env node
// Converts the pre-processed JSON Schemas into a Zod TypeScript file.
// Run via: pnpm generate:types  (Python export runs first)

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { jsonSchemaToZod } from "json-schema-to-zod";

const dir = dirname(fileURLToPath(import.meta.url));
const generated = join(dir, "../src/generated");
const read = (f) => JSON.parse(readFileSync(join(generated, f), "utf-8"));

const header = `\
// ⚠️  AUTO-GENERATED — do not edit.
// Source of truth: backend/app/rooms/protocol.py
// Regenerate:      pnpm generate:types
`;

// Server schema: esm module adds the import + exports the const.
const serverZod = jsonSchemaToZod(read("server-event.schema.json"), { name: "ServerEventSchema", module: "esm" });

// Client schema: get the bare expression, then declare and export it manually
// (avoids a duplicate `import { z } from "zod"` line).
const clientExpr = jsonSchemaToZod(read("client-event.schema.json"), { module: "none" });

const output = [
  header,
  serverZod,
  "export type ServerEvent = z.infer<typeof ServerEventSchema>;",
  "",
  `export const ClientEventSchema = ${clientExpr};`,
  "export type ClientEvent = z.infer<typeof ClientEventSchema>;",
].join("\n");

writeFileSync(join(generated, "protocol.ts"), output);

// Format the generated file so it's readable in code review
const { execSync } = await import("node:child_process");
try {
  execSync("./node_modules/.bin/biome format --write src/generated/protocol.ts", { stdio: "inherit" });
} catch {
  // biome is a dev dep — silently skip if unavailable (e.g. CI without devDeps)
}

console.log("✓ Generated frontend/src/generated/protocol.ts");
