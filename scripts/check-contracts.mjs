#!/usr/bin/env node

// Regenerate every contract artifact in place, then let git report drift:
// a modified or deleted tracked file is stale/missing, an untracked file is
// unexpected. `git status --porcelain` surfaces all three in one shot.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const paths = ["contracts", "frontend/src/generated"];

execFileSync("just", ["generate-contracts"], { cwd: root, stdio: "inherit" });

const drift = execFileSync("git", ["status", "--porcelain", "--", ...paths], { cwd: root, encoding: "utf8" }).trim();
if (drift) {
  console.error(
    `\nContract artifacts are out of date. Run \`just generate-contracts\` and commit the result.\n\n${drift}`,
  );
  process.exit(1);
}

console.log("✓ Contract files are up to date");
