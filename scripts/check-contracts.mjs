#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { execSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const trackedPaths = [
  "contracts/asyncapi/room-websocket.metadata.json",
  "contracts/asyncapi/room-websocket.asyncapi.yaml",
  "contracts/examples/client-events.json",
  "contracts/examples/server-events.json",
  "contracts/jsonschema/client-event.schema.json",
  "contracts/jsonschema/server-event.schema.json",
  "frontend/src/generated/protocol.ts",
];

function hashFile(path) {
  if (!existsSync(path)) return null;
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function snapshotFiles() {
  return new Map(trackedPaths.map((relativePath) => [relativePath, hashFile(resolve(root, relativePath))]));
}

function assertUnchanged(before, after) {
  const changed = trackedPaths.filter((relativePath) => before.get(relativePath) !== after.get(relativePath));
  if (changed.length > 0) {
    const details = changed.map((relativePath) => `- ${relativePath}`).join("\n");
    throw new Error(`Contract generation modified tracked files:\n${details}`);
  }
}

const before = snapshotFiles();

execSync("npm run generate:contracts", { cwd: root, stdio: "inherit" });
execSync("npm run generate:types", { cwd: root, stdio: "inherit" });
execSync("cd frontend && npm run validate:contracts", { cwd: root, stdio: "inherit", shell: "/bin/zsh" });

const after = snapshotFiles();
assertUnchanged(before, after);

console.log("✓ Contract files are up to date");
