import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const pluginEntry = import.meta.resolve("@sveltejs/vite-plugin-svelte");
const { preResolveOptions } = await import(/* @vite-ignore */ new URL("./utils/options.js", pluginEntry).href);
let directory: string | undefined;
afterEach(async () => {
  if (directory) await rm(directory, { recursive: true, force: true });
});

describe("Svelte plugin configuration", () => {
  it("preserves preprocessor instances inside option arrays", async () => {
    class Preprocessor {
      markup() {
        return { code: "processed" };
      }
    }
    const preprocessor = new Preprocessor();
    const options = await preResolveOptions(
      { configFile: false, preprocess: [preprocessor] },
      { root: process.cwd() },
      { command: "build", mode: "production" },
    );
    expect(options.preprocess[0]).toBe(preprocessor);
    expect(options.preprocess[0].markup()).toEqual({ code: "processed" });
  });
  it("preserves array overrides and object prototypes when merging configuration", async () => {
    directory = await mkdtemp(join(tmpdir(), "svelte-config-"));
    const configFile = join(directory, "svelte.config.mjs");
    await writeFile(configFile, "export default { compilerOptions: null, extensions: ['.old'] };\n");
    const compilerOptions = JSON.parse('{"__proto__":{"injected":true},"dev":false}');
    const options = await preResolveOptions(
      { configFile, compilerOptions, extensions: [".svelte"] },
      { root: process.cwd() },
      { command: "build", mode: "production" },
    );
    expect(options.extensions).toEqual([".svelte"]);
    expect(options.compilerOptions.dev).toBe(false);
    expect(options.compilerOptions.injected).toBeUndefined();
    expect(Object.getPrototypeOf(options.compilerOptions)).toBe(Object.prototype);
  });
});
