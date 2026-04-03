#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { execSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const trackedPaths = [
  "contracts/room-websocket.metadata.json",
  "contracts/room-websocket.asyncapi.yaml",
  "contracts/room-events.json",
  "contracts/client-events.examples.json",
  "contracts/server-events.examples.json",
  "contracts/jsonschema/client-event.schema.json",
  "contracts/jsonschema/server-event.schema.json",
  "frontend/src/generated/protocol.ts",
];

function readCatalogEventPaths() {
  const catalogPath = resolve(root, "contracts/room-events.json");
  const catalog = JSON.parse(readFileSync(catalogPath, "utf8"));
  return [
    "contracts/jsonschema/client-events/index.json",
    "contracts/jsonschema/server-events/index.json",
    ...Object.keys(catalog.client).map((eventType) => `contracts/jsonschema/client-events/${eventType}.schema.json`),
    ...Object.keys(catalog.server).map((eventType) => `contracts/jsonschema/server-events/${eventType}.schema.json`),
  ];
}

function hashFile(path) {
  if (!existsSync(path)) return null;
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function snapshotFiles() {
  const allPaths = [...new Set([...trackedPaths, ...readCatalogEventPaths()])];
  return new Map(allPaths.map((relativePath) => [relativePath, hashFile(resolve(root, relativePath))]));
}

function assertUnchanged(before, after) {
  const allPaths = [...new Set([...before.keys(), ...after.keys()])];
  const changed = allPaths.filter((relativePath) => before.get(relativePath) !== after.get(relativePath));
  if (changed.length > 0) {
    const details = changed.map((relativePath) => `- ${relativePath}`).join("\n");
    throw new Error(`Contract generation modified tracked files:\n${details}`);
  }
}

const before = snapshotFiles();

execSync("npm run contracts:generate", { cwd: root, stdio: "inherit" });
execSync("npm run contracts:types", { cwd: root, stdio: "inherit" });
execSync("cd frontend && npm run contracts:validate", { cwd: root, stdio: "inherit", shell: "/bin/zsh" });

const after = snapshotFiles();
assertUnchanged(before, after);

console.log("✓ Contract files are up to date");
