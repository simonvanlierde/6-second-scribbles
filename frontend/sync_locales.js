import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const localesDir = join(here, "src", "locales");
const enKeys = JSON.parse(readFileSync(join(localesDir, "en.json"), "utf8"));

const targets = [
  "de.json",
  "es.json",
  "fr.json",
  "it.json",
  "nl.json",
  "pt.json",
  "pl.json",
  "ja.json",
  "ko.json",
  "zh-CN.json",
  "zh-TW.json",
];

function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (source[key] instanceof Object && key in target) {
      Object.assign(source[key], deepMerge(target[key], source[key]));
    }
  }
  Object.assign(target || {}, source);
  return target;
}

for (const file of targets) {
  const p = join(localesDir, file);
  const data = JSON.parse(readFileSync(p, "utf8"));
  const merged = deepMerge(JSON.parse(JSON.stringify(enKeys)), data);
  writeFileSync(p, `${JSON.stringify(merged, null, 2)}\n`);
  console.log(`Updated ${file}`);
}
