// cspell:ignore multijoueur Inspiré
import { render } from "@testing-library/svelte";
import { tick } from "svelte";
import { afterEach, expect, it } from "vitest";
import AboutDialog from "@/components/home/AboutDialog.svelte";
import { setLocale } from "@/i18n";

afterEach(async () => {
  await setLocale("en");
});

it("renders translated attribution and preserves links when the locale changes", async () => {
  await setLocale("en");
  const { container } = render(AboutDialog, { open: true });
  const paragraph = container.querySelector(".about-text");
  if (!paragraph) throw new Error("About attribution is missing");
  expect(paragraph.textContent).toContain("A multiplayer web version of");
  expect(paragraph.textContent).toContain("by Gamely Games");
  expect(paragraph.textContent).toContain("Inspired by");

  await setLocale("fr");
  await tick();
  expect(paragraph.textContent).toContain("Une version Web multijoueur de");
  expect(paragraph.textContent).toContain("par Gamely Games");
  expect(paragraph.textContent).toContain("Inspiré par");
  expect([...paragraph.querySelectorAll("a")].map((link) => [link.textContent?.trim(), link.href])).toEqual([
    ["Six Second Scribbles", "https://gamelygames.com/products/six-second-scribbles"],
    ["Oliver Culley de Lange's solo version", "https://github.com/OliverCulleyDeLange/6ss"],
    ["Source on GitHub", "https://github.com/simonvanlierde/6-second-scribbles"],
  ]);
  expect(paragraph.textContent).not.toMatch(/\{(?:original|inspiration|source)\}/);
});
