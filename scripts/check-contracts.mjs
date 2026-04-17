#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const backendDir = join(root, "backend");
const frontendDir = join(root, "frontend");
const tempRoot = mkdtempSync(join(tmpdir(), "6ss-contracts-check-"));
const tempContractsDir = join(tempRoot, "contracts");
const tempFrontendDir = join(tempRoot, "frontend");
const tempGeneratedDir = join(tempFrontendDir, "src", "generated");
const uvCacheDir = join(tempRoot, "uv-cache");
const tempBiomeConfigPath = join(tempRoot, "biome.json");
const tempFrontendBiomeConfigPath = join(tempFrontendDir, "biome.json");
const backendGenerateArgs = ["run", "--project", ".", "python", "-m", "scripts.generate_contracts"];
const frontendGenerateArgs = ["run", "contracts:generate"];
const tempContractsFormatTargets = [
  join(tempContractsDir, "openapi.json"),
  join(tempContractsDir, "room-events.json"),
  join(tempContractsDir, "jsonschema"),
];
const tempFrontendFormatTargets = [join(tempGeneratedDir, "protocol.ts"), join(tempGeneratedDir, "api.ts")];

writeFileSync(
  tempBiomeConfigPath,
  JSON.stringify(
    {
      $schema: "https://biomejs.dev/schemas/2.4.10/schema.json",
      files: {
        includes: ["contracts/**", "frontend-generated/**"],
      },
      formatter: {
        indentStyle: "space",
        lineWidth: 120,
      },
    },
    null,
    2,
  ),
);

mkdirSync(tempFrontendDir, { recursive: true });
writeFileSync(
  tempFrontendBiomeConfigPath,
  JSON.stringify(
    {
      $schema: "https://biomejs.dev/schemas/2.4.10/schema.json",
      files: {
        includes: ["**"],
      },
      formatter: {
        indentStyle: "space",
        lineWidth: 120,
      },
    },
    null,
    2,
  ),
);

const staticGeneratedPaths = [
  "contracts/room-events.json",
  "contracts/openapi.json",
  "contracts/jsonschema/client-event.schema.json",
  "contracts/jsonschema/server-event.schema.json",
  "frontend/src/generated/protocol.ts",
  "frontend/src/generated/api.ts",
];

function run(command, args, options) {
  execFileSync(command, args, {
    stdio: "inherit",
    ...options,
  });
}

function formatGeneratedFiles(configPath, files, cwd = root) {
  run("pnpm", ["exec", "biome", "format", "--write", "--config-path", configPath, ...files], { cwd });
}

function checkGeneratedFrontendFiles(files) {
  run("pnpm", ["exec", "biome", "check", "--write", "--config-path", tempFrontendBiomeConfigPath, ...files], {
    cwd: frontendDir,
  });
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function listFiles(rootDir, prefix) {
  if (!existsSync(rootDir)) {
    return [];
  }

  const entries = readdirSync(rootDir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const entryPath = join(rootDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listFiles(entryPath, prefix));
      continue;
    }
    files.push(relative(prefix, entryPath).replaceAll("\\", "/"));
  }
  return files.sort();
}

function expectedGeneratedPaths() {
  const catalog = readJson(join(tempContractsDir, "room-events.json"));
  return [
    ...staticGeneratedPaths,
    "contracts/jsonschema/client-events/index.json",
    "contracts/jsonschema/server-events/index.json",
    ...Object.keys(catalog.client)
      .sort()
      .map((eventType) => `contracts/jsonschema/client-events/${eventType}.schema.json`),
    ...Object.keys(catalog.server)
      .sort()
      .map((eventType) => `contracts/jsonschema/server-events/${eventType}.schema.json`),
  ];
}

function actualGeneratedPaths() {
  return [
    ...staticGeneratedPaths.filter((relativePath) => existsSync(join(root, relativePath))),
    ...listFiles(join(root, "contracts/jsonschema"), root),
    ...listFiles(join(root, "frontend/src/generated"), root),
  ]
    .filter((value, index, array) => array.indexOf(value) === index)
    .sort();
}

function fileContent(path) {
  return existsSync(path) ? readFileSync(path) : null;
}

function expectedFilePath(relativePath) {
  if (relativePath.startsWith("frontend/src/generated/")) {
    return join(tempGeneratedDir, relativePath.replace("frontend/src/generated/", ""));
  }

  return join(tempContractsDir, relativePath.replace("contracts/", ""));
}

function compareOutputs() {
  const expectedPaths = expectedGeneratedPaths();
  const actualPaths = actualGeneratedPaths();

  const missing = expectedPaths.filter((relativePath) => !actualPaths.includes(relativePath));
  const unexpected = actualPaths.filter((relativePath) => !expectedPaths.includes(relativePath));
  const changed = expectedPaths.filter((relativePath) => {
    if (missing.includes(relativePath)) {
      return false;
    }

    const expectedPath = expectedFilePath(relativePath);
    const actualPath = join(root, relativePath);
    return Buffer.compare(fileContent(expectedPath), fileContent(actualPath)) !== 0;
  });

  return { missing, unexpected, changed };
}

function printFailure({ missing, unexpected, changed }) {
  const lines = ["Contract artifacts are out of date. Run `just generate-contracts`."];

  if (missing.length > 0) {
    lines.push("", "Missing generated files:");
    lines.push(...missing.map((relativePath) => `- ${relativePath}`));
  }

  if (unexpected.length > 0) {
    lines.push("", "Unexpected generated files:");
    lines.push(...unexpected.map((relativePath) => `- ${relativePath}`));
  }

  if (changed.length > 0) {
    lines.push("", "Stale generated files:");
    lines.push(...changed.map((relativePath) => `- ${relativePath}`));
  }

  throw new Error(lines.join("\n"));
}

try {
  run("uv", backendGenerateArgs, {
    cwd: backendDir,
    env: {
      ...process.env,
      CONTRACTS_ROOT: tempContractsDir,
      UV_CACHE_DIR: uvCacheDir,
    },
  });

  formatGeneratedFiles(tempRoot, tempContractsFormatTargets);

  run("pnpm", frontendGenerateArgs, {
    cwd: frontendDir,
    env: {
      ...process.env,
      CONTRACTS_DIR: tempContractsDir,
      FRONTEND_GENERATED_DIR: tempGeneratedDir,
    },
  });

  checkGeneratedFrontendFiles(tempFrontendFormatTargets);

  const diff = compareOutputs();
  if (diff.missing.length > 0 || diff.unexpected.length > 0 || diff.changed.length > 0) {
    printFailure(diff);
  }

  console.log("✓ Contract files are up to date");
} finally {
  rmSync(tempRoot, { force: true, recursive: true });
}
