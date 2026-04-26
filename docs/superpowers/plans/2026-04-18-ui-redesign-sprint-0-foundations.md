# UI Redesign · Sprint 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock in the design system (tokens, fonts, motion, primitive components, composables, demo route) so subsequent screen-rebuild sprints can compose them without revisiting foundations.

**Architecture:** Single new `styles/tokens.css` exposing every design token as CSS custom properties (light + dark via `prefers-color-scheme` and a `[data-theme]` override). All UI primitives live in `frontend/src/components/ui/Hd*.vue` and consume tokens — no hardcoded hex, no arbitrary Tailwind values. Three new composables (`useSound`, `useAvatar`, `useReactions`) sit in `frontend/src/composables/`. A demo route `/__ds` mounts every primitive on a single page for visual QA and contrast checks. No existing screens change in this sprint.

**Tech Stack:** Vue 3, Vite, Tailwind 4, TypeScript, Vitest, `@vue/test-utils`, plus new deps: `@fontsource/kalam`, `@fontsource/patrick-hand`, `@vueuse/motion`, `howler`, `html-to-image`.

---

## Source-of-truth references

- Design spec: [docs/superpowers/specs/2026-04-18-ui-redesign-2026-design.md](../specs/2026-04-18-ui-redesign-2026-design.md). When in doubt about a token value, component variant, or behaviour, defer to the spec.
- Existing test patterns: [frontend/src/components/\_\_tests\_\_/RoomCodeInput.spec.ts](../../../frontend/src/components/__tests__/RoomCodeInput.spec.ts) (smoke + interaction style).
- Existing dialog primitive being replaced: [frontend/src/components/ConfirmDialog.vue](../../../frontend/src/components/ConfirmDialog.vue).
- Existing toast primitive being replaced: [frontend/src/components/ToastContainer.vue](../../../frontend/src/components/ToastContainer.vue) and [frontend/src/composables/notifications.ts](../../../frontend/src/composables/notifications.ts).

## File structure

### Files created

|Path|Responsibility|
|---|---|
|`frontend/src/styles/tokens.css`|All design-system CSS custom properties (color light/dark, type, motion, radius, shadow, rotation).|
|`frontend/src/styles/texture.svg`|SVG noise filter used as paper-grain `body::before` overlay.|
|`frontend/src/styles/fonts.css`|Self-hosted font-face declarations + `font-display: swap`.|
|`frontend/src/components/ui/HdButton.vue`|Primary / secondary / success / ghost button.|
|`frontend/src/components/ui/HdCard.vue`|`default` and `postit` variants.|
|`frontend/src/components/ui/HdInput.vue`|`default` and `code` variants.|
|`frontend/src/components/ui/HdAvatar.vue`|Sizes `sm` / `md` / `lg` + colour + initial.|
|`frontend/src/components/ui/HdTimer.vue`|Calm vs urgent based on `urgentAt` threshold prop.|
|`frontend/src/components/ui/HdPill.vue`|`default` / `info` / `success` chip.|
|`frontend/src/components/ui/HdReactionPad.vue`|5-icon emoji tray emitting `react`.|
|`frontend/src/components/ui/HdToast.vue`|Replacement for `ToastContainer` rendering.|
|`frontend/src/components/ui/HdDialog.vue`|Replacement for `ConfirmDialog`.|
|`frontend/src/composables/useSound.ts`|Howler-backed sound layer with persisted toggle.|
|`frontend/src/composables/useAvatar.ts`|Color + initial helpers; deterministic colour for a player id.|
|`frontend/src/composables/useReactions.ts`|Skeleton for live-reaction state (full WebSocket wiring lands in Sprint 3).|
|`frontend/src/views/DesignSystemView.vue`|`/__ds` demo route showing every primitive.|
|`frontend/src/components/ui/__tests__/HdButton.spec.ts`|Smoke + variant + emit tests.|
|`frontend/src/components/ui/__tests__/HdCard.spec.ts`|Smoke + variant tests.|
|`frontend/src/components/ui/__tests__/HdInput.spec.ts`|Smoke + v-model + variant tests.|
|`frontend/src/components/ui/__tests__/HdAvatar.spec.ts`|Smoke + size + colour tests.|
|`frontend/src/components/ui/__tests__/HdTimer.spec.ts`|Calm/urgent threshold tests.|
|`frontend/src/components/ui/__tests__/HdPill.spec.ts`|Smoke test.|
|`frontend/src/components/ui/__tests__/HdReactionPad.spec.ts`|Emit test.|
|`frontend/src/components/ui/__tests__/HdToast.spec.ts`|Render-from-store test.|
|`frontend/src/components/ui/__tests__/HdDialog.spec.ts`|v-model open/close + emit tests.|
|`frontend/src/composables/__tests__/useAvatar.spec.ts`|Deterministic colour assignment test.|
|`frontend/src/composables/__tests__/useSound.spec.ts`|Toggle + Howler-mock invocation test.|
|`frontend/public/sounds/.gitkeep`|Placeholder for future audio assets (no audio in this sprint).|

### Files modified

|Path|Change|
|---|---|
|`frontend/package.json`|Add 5 deps + 1 dev-dep.|
|`frontend/src/assets/main.css`|Replace ad-hoc `@theme` block with import of `tokens.css` + `fonts.css`; add Tailwind theme bridge.|
|`frontend/src/main.ts`|Register `@vueuse/motion` plugin.|
|`frontend/src/router/index.ts`|Add `/__ds` route (only mounted in dev).|

### Files NOT changed in this sprint (deferred to Sprint 1+)

- All existing views (`HomeView`, `RoomView`, etc.) and existing components (`CreateJoinCard`, `DrawingPhase`, etc.) — they keep using their current styles.
- `ConfirmDialog.vue` and `ToastContainer.vue` stay in place; the new `HdDialog`/`HdToast` are added alongside. Migration of callers happens in Sprint 1.
- All backend code.

## Conventions for this sprint

- All components use `<script setup lang="ts">` and `withDefaults(defineProps<...>())`.
- All components forward `class` and `style` (default Vue 3 behaviour with single root element; ensure single root).
- Every interactive element has a visible `:focus-visible` ring sourced from `--ring`.
- No emoji except inside `HdReactionPad`.
- Tests use `mount` from `@vue/test-utils` + Vitest assertions.
- Commit message convention: matches repo (`feat(ds): ...`, `chore(ds): ...`, `test(ds): ...`).

---

## Task 1: Install new dependencies

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/pnpm-lock.yaml` (auto-generated)

- [ ] **Step 1: Install runtime dependencies**

Run:

```bash
cd frontend && pnpm add @fontsource/kalam @fontsource/patrick-hand @vueuse/motion howler html-to-image
```

Expected: `package.json` `dependencies` gains 5 entries, lockfile updates.

- [ ] **Step 2: Install type definitions for Howler**

Run:

```bash
cd frontend && pnpm add -D @types/howler
```

Expected: `package.json` `devDependencies` gains `@types/howler`.

- [ ] **Step 3: Verify install**

Run:

```bash
cd frontend && pnpm install --frozen-lockfile && pnpm type-check
```

Expected: lockfile reconciled (no changes), type-check passes.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(frontend): add design-system runtime deps"
```

## Task 2: Create design tokens CSS

**Files:**

- Create: `frontend/src/styles/tokens.css`

- [ ] **Step 1: Create the tokens file**

Create `frontend/src/styles/tokens.css` with this exact content:

```css
/* Design tokens for the 2026 redesign. Source of truth for color, type,

 * motion, radius, shadow, rotation. Consumed by Tailwind theme + components. */

:root {
  /* Color — light (default) */
  --color-paper: #FDFBF7;
  --color-card: #FFFFFF;
  --color-ink: #2D2D2D;
  --color-ink-muted: #5e5847;
  --color-marker-red: #FF4D4D;
  --color-ballpoint-blue: #2D5DA1;
  --color-highlighter-yellow: #FFF9C4;
  --color-meadow-green: #B5E6B5;

  /* Avatar palette (decorative only) */
  --avatar-1: #FFB4A2;
  --avatar-2: #B5E6B5;
  --avatar-3: #ADD8E6;
  --avatar-4: #FFE08A;
  --avatar-5: #E0BBFF;
  --avatar-6: #FFCBA4;

  /* Semantic aliases */
  --color-bg: var(--color-paper);
  --color-surface: var(--color-card);
  --color-text: var(--color-ink);
  --color-text-muted: var(--color-ink-muted);
  --color-primary: var(--color-marker-red);
  --color-secondary: var(--color-ballpoint-blue);
  --color-accent: var(--color-highlighter-yellow);
  --color-success: var(--color-meadow-green);
  --color-danger: var(--color-marker-red);
  --color-ring: var(--color-ballpoint-blue);

  /* Typography */
  --font-display: "Kalam", "Caveat", system-ui, sans-serif;
  --font-body: "Patrick Hand", system-ui, sans-serif;
  --font-mono: ui-monospace, "SFMono-Regular", "JetBrains Mono", monospace;

  --text-display-lg: 56px;
  --text-display-md: 40px;
  --text-display-sm: 32px;
  --text-heading-lg: 28px;
  --text-heading-md: 22px;
  --text-heading-sm: 18px;
  --text-body-lg: 18px;
  --text-body-md: 16px;
  --text-label-md: 14px;
  --text-label-sm: 13px;

  /* Radius (wobbly — four different per corner) */
  --r-card: 16px 22px 14px 18px;
  --r-button: 14px 22px 16px 12px;
  --r-input: 14px 18px 12px 16px;
  --r-pill: 8px 12px 8px 12px;
  --r-avatar: 11px 14px 10px 13px;

  /* Borders */
  --border-input: 2px;
  --border-card: 2.5px;
  --border-button: 2.5px;

  /* Shadow (hard offset, no blur) */
  --shadow-card: 4px 4px 0 var(--color-ink);
  --shadow-button: 3px 3px 0 var(--color-ink);
  --shadow-pill: 2px 2px 0 var(--color-ink);
  --shadow-avatar: 2.5px 2.5px 0 var(--color-ink);

  /* Rotation defaults (per-element overridable via --rotate) */
  --rotate-card: -0.4deg;
  --rotate-button: -0.5deg;
  --rotate-postit: -1.2deg;

  /* Motion */
  --motion-fast: 150ms;
  --motion-base: 220ms;
  --motion-slow: 360ms;
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);

  /* Spacing scale (4px base) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  color-scheme: light;
}

/* Dark mode — applied via prefers-color-scheme OR explicit [data-theme="dark"] */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-paper: #1A1614;
    --color-card: #231E1B;
    --color-ink: #F2EDE2;
    --color-ink-muted: #b5ada0;
    --color-marker-red: #FF6B6B;
    --color-ballpoint-blue: #7BA4E6;
    --color-highlighter-yellow: #FFE066;
    --color-meadow-green: #9CDB9C;
    color-scheme: dark;
  }
}

:root[data-theme="dark"] {
  --color-paper: #1A1614;
  --color-card: #231E1B;
  --color-ink: #F2EDE2;
  --color-ink-muted: #b5ada0;
  --color-marker-red: #FF6B6B;
  --color-ballpoint-blue: #7BA4E6;
  --color-highlighter-yellow: #FFE066;
  --color-meadow-green: #9CDB9C;
  color-scheme: dark;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  :root {
    --motion-fast: 0ms;
    --motion-base: 0ms;
    --motion-slow: 0ms;
  }
}
```

- [ ] **Step 2: Smoke-check the file imports cleanly**

Run:

```bash
cd frontend && pnpm dev
```

Open browser to the running dev URL (default `http://localhost:5173`). The page is unchanged at this point because nothing imports `tokens.css` yet — verify only that the dev server starts without errors. Then `Ctrl+C` to stop.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/tokens.css
git commit -m "feat(ds): add design tokens (color, type, motion, radius, shadow)"
```

## Task 3: Wire fonts (self-hosted via @fontsource)

**Files:**

- Create: `frontend/src/styles/fonts.css`

- [ ] **Step 1: Create the fonts entry CSS**

Create `frontend/src/styles/fonts.css`:

```css
/* Self-hosted display + body fonts via @fontsource */
@import "@fontsource/kalam/400.css";
@import "@fontsource/kalam/700.css";
@import "@fontsource/patrick-hand/400.css";
```

These three subset CSS files come from the npm packages installed in Task 1. They register `@font-face` rules and use `font-display: swap` by default.

- [ ] **Step 2: Verify import resolution**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes (CSS imports are resolved by Vite at runtime; type-check just verifies TS files are clean).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/fonts.css
git commit -m "feat(ds): self-host Kalam (display) and Patrick Hand (body) fonts"
```

## Task 4: Wire tokens + fonts into main.css

**Files:**

- Modify: `frontend/src/assets/main.css`

- [ ] **Step 1: Read the current main.css**

Run:

```bash
cat frontend/src/assets/main.css
```

Expected: shows the current `@theme` block with old purple/blue tokens.

- [ ] **Step 2: Replace the file content**

Overwrite `frontend/src/assets/main.css` with:

```css
@import "tailwindcss";
@import "../styles/fonts.css";
@import "../styles/tokens.css";

/* Bridge our CSS tokens into Tailwind's theme so utilities like `bg-paper`,

 * `text-ink`, `rounded-card`, `shadow-card` work. */
@theme {
  --color-paper: var(--color-paper);
  --color-card: var(--color-card);
  --color-ink: var(--color-ink);
  --color-ink-muted: var(--color-ink-muted);
  --color-marker-red: var(--color-marker-red);
  --color-ballpoint-blue: var(--color-ballpoint-blue);
  --color-highlighter-yellow: var(--color-highlighter-yellow);
  --color-meadow-green: var(--color-meadow-green);

  --font-display: var(--font-display);
  --font-body: var(--font-body);
  --font-mono: var(--font-mono);

  --shadow-card: var(--shadow-card);
  --shadow-button: var(--shadow-button);
  --shadow-pill: var(--shadow-pill);
}

@layer base {
  body {
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-body);
    min-height: 100vh;
    font-size: var(--text-body-md);
    line-height: 1.5;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display);
    font-weight: 700;
    color: var(--color-text);
  }
  h1 { font-size: var(--text-display-md); }
  h2 { font-size: var(--text-heading-lg); }
  h3 { font-size: var(--text-heading-md); }
  h4 { font-size: var(--text-heading-sm); }
  /* Universal focus ring */
  *:focus-visible {
    outline: 3px solid var(--color-ring);
    outline-offset: 2px;
    border-radius: 4px;
  }
}
```

- [ ] **Step 3: Run dev server and visually verify**

Run:

```bash
cd frontend && pnpm dev
```

Open the running dev URL. The home screen now renders on cream paper with hand-drawn fonts and slightly different headings. **Existing layouts will look broken in places** — this is expected; existing components still use the old gradient/purple references which no longer resolve to the same colours. This is acceptable for Sprint 0; existing screens will be rebuilt in Sprint 1+.

Verify in DevTools that `body` computed `background-color` is `rgb(253, 251, 247)` (the cream paper). `Ctrl+C` to stop.

- [ ] **Step 4: Run type-check**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes (no TS files changed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(ds): replace gradient theme with cream paper + ink design tokens"
```

## Task 5: Add paper-grain texture overlay

**Files:**

- Create: `frontend/src/styles/texture.svg`
- Modify: `frontend/src/assets/main.css`

- [ ] **Step 1: Create the SVG noise filter**

Create `frontend/src/styles/texture.svg` with this content (a tiny SVG with a `feTurbulence` noise filter that renders as a 200×200 tile):

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <filter id="n">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#n)"/>
</svg>
```

- [ ] **Step 2: Add the body overlay rule to main.css**

Append to `frontend/src/assets/main.css` (inside the `@layer base` block, immediately before the closing `}`):

```css
  body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image: url("../styles/texture.svg");
    background-size: 200px 200px;
    opacity: 0.04;
    mix-blend-mode: multiply;
    z-index: 0;
  }
```

- [ ] **Step 3: Verify the overlay renders**

Run `pnpm dev` and visually confirm a subtle grain on the cream background. In DevTools, a `body::before` pseudo-element exists with the texture image. `Ctrl+C` to stop.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/texture.svg frontend/src/assets/main.css
git commit -m "feat(ds): add paper-grain noise overlay"
```

## Task 6: Register @vueuse/motion plugin

**Files:**

- Modify: `frontend/src/main.ts`

- [ ] **Step 1: Add the plugin import + registration**

Edit `frontend/src/main.ts`. Add `import { MotionPlugin } from "@vueuse/motion";` near the other imports, and `app.use(MotionPlugin);` after `app.use(i18n);`. Final file:

```ts
import "./assets/main.css";

import { MotionPlugin } from "@vueuse/motion";
import { createPinia } from "pinia";
import { createPersistedState } from "pinia-plugin-persistedstate";
import { createApp } from "vue";

import App from "./App.vue";
import { i18n } from "./i18n";
import router from "./router";

const app = createApp(App);

const pinia = createPinia();
pinia.use(createPersistedState());

app.use(pinia);
app.use(router);
app.use(i18n);
app.use(MotionPlugin);

app.mount("#app");
```

- [ ] **Step 2: Verify**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/main.ts
git commit -m "feat(ds): register @vueuse/motion plugin"
```

## Task 7: useAvatar composable

**Files:**

- Create: `frontend/src/composables/useAvatar.ts`
- Test: `frontend/src/composables/__tests__/useAvatar.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/composables/__tests__/useAvatar.spec.ts`:

```ts
import { describe, expect, it } from "vitest";

import { AVATAR_COLORS, getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";

describe("useAvatar", () => {
  it("exposes 6 token colors", () => {
    expect(AVATAR_COLORS).toHaveLength(6);
    for (const c of AVATAR_COLORS) {
      expect(c).toMatch(/^var\(--avatar-\d\)$/);
    }
  });

  it("returns a deterministic color for the same player id", () => {
    const a = getAvatarColor("player-abc-123");
    const b = getAvatarColor("player-abc-123");
    expect(a).toBe(b);
    expect(AVATAR_COLORS).toContain(a);
  });

  it("returns different colors for different ids most of the time", () => {
    const set = new Set(["a", "b", "c", "d", "e", "f"].map(getAvatarColor));
    expect(set.size).toBeGreaterThan(1);
  });

  it("returns the uppercased first non-whitespace character of a name", () => {
    expect(getAvatarInitial("simon")).toBe("S");
    expect(getAvatarInitial("  jules ")).toBe("J");
  });

  it("returns ? for an empty name", () => {
    expect(getAvatarInitial("")).toBe("?");
    expect(getAvatarInitial("   ")).toBe("?");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- composables/useAvatar
```

Expected: FAIL with "Cannot find module '@/composables/useAvatar'".

- [ ] **Step 3: Implement the composable**

Create `frontend/src/composables/useAvatar.ts`:

```ts
export const AVATAR_COLORS = [
  "var(--avatar-1)",
  "var(--avatar-2)",
  "var(--avatar-3)",
  "var(--avatar-4)",
  "var(--avatar-5)",
  "var(--avatar-6)",
] as const;

export type AvatarColor = (typeof AVATAR_COLORS)[number];

/** Hash a player id into a stable index in [0, AVATAR_COLORS.length). */
function hash(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i += 1) {
    h = (h * 31 + id.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function getAvatarColor(playerId: string): AvatarColor {
  const idx = hash(playerId) % AVATAR_COLORS.length;
  // Non-null: AVATAR_COLORS has length 6, idx is always in range.
  return AVATAR_COLORS[idx] as AvatarColor;
}

export function getAvatarInitial(name: string): string {
  const trimmed = name.trim();
  if (trimmed.length === 0) return "?";
  return trimmed.charAt(0).toUpperCase();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- composables/useAvatar
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useAvatar.ts frontend/src/composables/__tests__/useAvatar.spec.ts
git commit -m "feat(ds): add useAvatar composable (deterministic color + initial helpers)"
```

## Task 8: useSound composable (Howler wrapper + persisted toggle)

**Files:**

- Create: `frontend/src/composables/useSound.ts`
- Test: `frontend/src/composables/__tests__/useSound.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/composables/__tests__/useSound.spec.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";

const playMock = vi.fn();
const muteMock = vi.fn();

vi.mock("howler", () => ({
  Howl: vi.fn().mockImplementation(() => ({
    play: playMock,
    mute: muteMock,
  })),
}));

import { SOUND_KEYS, useSound } from "@/composables/useSound";

describe("useSound", () => {
  beforeEach(() => {
    playMock.mockClear();
    muteMock.mockClear();
    localStorage.clear();
  });

  it("exposes the expected sound keys", () => {
    expect(Object.keys(SOUND_KEYS)).toEqual([
      "roundStart",
      "tick",
      "reveal",
      "winner",
      "click",
    ]);
  });

  it("is disabled by default and does not call play", () => {
    const { enabled, play } = useSound();
    expect(enabled.value).toBe(false);
    play("click");
    expect(playMock).not.toHaveBeenCalled();
  });

  it("plays when enabled is set to true", () => {
    const { enabled, play } = useSound();
    enabled.value = true;
    play("click");
    expect(playMock).toHaveBeenCalledTimes(1);
  });

  it("persists the enabled flag to localStorage", () => {
    const { enabled } = useSound();
    enabled.value = true;
    expect(localStorage.getItem("ds:sound-enabled")).toBe("true");

    const second = useSound();
    expect(second.enabled.value).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- composables/useSound
```

Expected: FAIL with "Cannot find module '@/composables/useSound'".

- [ ] **Step 3: Implement the composable**

Create `frontend/src/composables/useSound.ts`:

```ts
import { Howl } from "howler";
import { ref, watch } from "vue";

export const SOUND_KEYS = {
  roundStart: "/sounds/round-start.ogg",
  tick: "/sounds/tick.ogg",
  reveal: "/sounds/reveal.ogg",
  winner: "/sounds/winner.ogg",
  click: "/sounds/click.ogg",
} as const;

export type SoundKey = keyof typeof SOUND_KEYS;

const STORAGE_KEY = "ds:sound-enabled";

const enabled = ref<boolean>(readEnabled());
const cache = new Map<SoundKey, Howl>();

function readEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

watch(enabled, (v) => {
  try {
    localStorage.setItem(STORAGE_KEY, v ? "true" : "false");
  } catch {
    /* localStorage unavailable */
  }
});

function getHowl(key: SoundKey): Howl {
  let h = cache.get(key);
  if (!h) {
    h = new Howl({ src: [SOUND_KEYS[key]], volume: 0.5, preload: true });
    cache.set(key, h);
  }
  return h;
}

export function useSound() {
  function play(key: SoundKey): void {
    if (!enabled.value) return;
    getHowl(key).play();
  }

  return { enabled, play };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- composables/useSound
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useSound.ts frontend/src/composables/__tests__/useSound.spec.ts
git commit -m "feat(ds): add useSound composable with Howler + persisted toggle"
```

## Task 9: useReactions composable (skeleton)

**Files:**

- Create: `frontend/src/composables/useReactions.ts`

The full WebSocket round-trip lands in Sprint 3 (round-results screen). This sprint ships a typed skeleton and a component-local store so `HdReactionPad` has something to dispatch into during the demo route.

- [ ] **Step 1: Implement the skeleton**

Create `frontend/src/composables/useReactions.ts`:

```ts
import { reactive } from "vue";

export const REACTION_KEYS = ["laugh", "shock", "art", "mind-blown", "think"] as const;
export type ReactionKey = (typeof REACTION_KEYS)[number];

export const REACTION_EMOJI: Record<ReactionKey, string> = {
  laugh: "😂",
  shock: "😱",
  art: "🎨",
  "mind-blown": "🤯",
  think: "🤔",
};

type Counts = Record<ReactionKey, number>;
type ReactionsState = Record<string, Counts>;

const state = reactive<ReactionsState>({});

function emptyCounts(): Counts {
  return { laugh: 0, shock: 0, art: 0, "mind-blown": 0, think: 0 };
}

export function useReactions() {
  function add(targetId: string, key: ReactionKey): void {
    if (!state[targetId]) state[targetId] = emptyCounts();
    state[targetId][key] += 1;
  }

  function countsFor(targetId: string): Counts {
    return state[targetId] ?? emptyCounts();
  }

  function clear(): void {
    for (const k of Object.keys(state)) delete state[k];
  }

  return { add, countsFor, clear };
}
```

- [ ] **Step 2: Type-check**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useReactions.ts
git commit -m "feat(ds): add useReactions composable skeleton"
```

## Task 10: HdButton component

**Files:**

- Create: `frontend/src/components/ui/HdButton.vue`
- Test: `frontend/src/components/ui/__tests__/HdButton.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdButton.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdButton from "@/components/ui/HdButton.vue";

describe("HdButton", () => {
  it("renders default slot text", () => {
    const w = mount(HdButton, { slots: { default: "Click me" } });
    expect(w.text()).toBe("Click me");
  });

  it("emits click when pressed", async () => {
    const w = mount(HdButton, { slots: { default: "Go" } });
    await w.trigger("click");
    expect(w.emitted("click")).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = mount(HdButton, { props: { disabled: true }, slots: { default: "Go" } });
    await w.trigger("click");
    expect(w.emitted("click")).toBeUndefined();
  });

  it("applies the variant class", () => {
    const primary = mount(HdButton, { props: { variant: "primary" }, slots: { default: "P" } });
    const secondary = mount(HdButton, { props: { variant: "secondary" }, slots: { default: "S" } });
    expect(primary.classes()).toContain("hd-btn--primary");
    expect(secondary.classes()).toContain("hd-btn--secondary");
  });

  it("renders as <button type='button'> by default", () => {
    const w = mount(HdButton, { slots: { default: "X" } });
    expect(w.element.tagName).toBe("BUTTON");
    expect(w.attributes("type")).toBe("button");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdButton
```

Expected: FAIL with "Cannot find module '@/components/ui/HdButton.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdButton.vue`:

```vue
<script setup lang="ts">
type Variant = "primary" | "secondary" | "success" | "ghost";

interface Props {
  variant?: Variant;
  type?: "button" | "submit";
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "primary",
  type: "button",
  disabled: false,
});

defineEmits<{ click: [MouseEvent] }>();
</script>

<template>
  <button
    :type="props.type"
    :disabled="props.disabled"
    class="hd-btn"
    :class="`hd-btn--${props.variant}`"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.hd-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1;
  border: var(--border-button) solid var(--color-ink);
  border-radius: var(--r-button);
  box-shadow: var(--shadow-button);
  transform: rotate(var(--rotate-button));
  cursor: pointer;
  min-height: 44px;
  min-width: 44px;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-btn:active:not(:disabled) {
  transform: rotate(var(--rotate-button)) translate(3px, 3px);
  box-shadow: 0 0 0 var(--color-ink);
}
.hd-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.hd-btn--primary {
  background: var(--color-marker-red);
  color: white;
}
.hd-btn--secondary {
  background: var(--color-card);
  color: var(--color-ink);
  --rotate-button: 0.4deg;
}
.hd-btn--success {
  background: var(--color-meadow-green);
  color: var(--color-ink);
  --rotate-button: -0.3deg;
  border-radius: 12px 18px 14px 22px;
}
.hd-btn--ghost {
  background: transparent;
  color: var(--color-ballpoint-blue);
  border: 0;
  box-shadow: none;
  text-decoration: underline wavy;
  text-underline-offset: 4px;
  transform: none;
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 1rem;
  padding: 8px 12px;
}
.hd-btn--ghost:active:not(:disabled) {
  transform: none;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdButton
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdButton.vue frontend/src/components/ui/__tests__/HdButton.spec.ts
git commit -m "feat(ds): add HdButton primitive (primary/secondary/success/ghost)"
```

## Task 11: HdCard component

**Files:**

- Create: `frontend/src/components/ui/HdCard.vue`
- Test: `frontend/src/components/ui/__tests__/HdCard.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdCard.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdCard from "@/components/ui/HdCard.vue";

describe("HdCard", () => {
  it("renders default slot", () => {
    const w = mount(HdCard, { slots: { default: "<p>hi</p>" } });
    expect(w.text()).toBe("hi");
  });

  it("applies the default variant class", () => {
    const w = mount(HdCard, { slots: { default: "x" } });
    expect(w.classes()).toContain("hd-card--default");
  });

  it("applies the postit variant class", () => {
    const w = mount(HdCard, { props: { variant: "postit" }, slots: { default: "x" } });
    expect(w.classes()).toContain("hd-card--postit");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdCard
```

Expected: FAIL with "Cannot find module '@/components/ui/HdCard.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdCard.vue`:

```vue
<script setup lang="ts">
type Variant = "default" | "postit";

interface Props {
  variant?: Variant;
}

const props = withDefaults(defineProps<Props>(), { variant: "default" });
</script>

<template>
  <div class="hd-card" :class="`hd-card--${props.variant}`">
    <slot />
  </div>
</template>

<style scoped>
.hd-card {
  padding: var(--space-4);
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  transform: rotate(var(--rotate-card));
}
.hd-card--default {
  background: var(--color-card);
}
.hd-card--postit {
  background: var(--color-highlighter-yellow);
  --rotate-card: var(--rotate-postit);
  border-width: 1px;
  border-color: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  box-shadow: 2px 4px 6px rgba(0, 0, 0, 0.16);
  font-size: 0.95rem;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdCard
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdCard.vue frontend/src/components/ui/__tests__/HdCard.spec.ts
git commit -m "feat(ds): add HdCard primitive (default + postit)"
```

## Task 12: HdInput component

**Files:**

- Create: `frontend/src/components/ui/HdInput.vue`
- Test: `frontend/src/components/ui/__tests__/HdInput.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdInput.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdInput from "@/components/ui/HdInput.vue";

describe("HdInput", () => {
  it("renders an input element", () => {
    const w = mount(HdInput);
    expect(w.find("input").exists()).toBe(true);
  });

  it("supports v-model via update:modelValue", async () => {
    const w = mount(HdInput, { props: { modelValue: "" } });
    await w.find("input").setValue("hello");
    expect(w.emitted("update:modelValue")?.[0]).toEqual(["hello"]);
  });

  it("renders the placeholder", () => {
    const w = mount(HdInput, { props: { placeholder: "type here" } });
    expect(w.find("input").attributes("placeholder")).toBe("type here");
  });

  it("applies the code variant class", () => {
    const w = mount(HdInput, { props: { variant: "code" } });
    expect(w.classes()).toContain("hd-input--code");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdInput
```

Expected: FAIL with "Cannot find module '@/components/ui/HdInput.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdInput.vue`:

```vue
<script setup lang="ts">
type Variant = "default" | "code";

interface Props {
  modelValue?: string;
  placeholder?: string;
  variant?: Variant;
  type?: string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: "",
  placeholder: "",
  variant: "default",
  type: "text",
  ariaLabel: undefined,
});

const emit = defineEmits<{ "update:modelValue": [string] }>();

function onInput(e: Event): void {
  emit("update:modelValue", (e.target as HTMLInputElement).value);
}
</script>

<template>
  <input
    :value="props.modelValue"
    :placeholder="props.placeholder"
    :type="props.type"
    :aria-label="props.ariaLabel"
    class="hd-input"
    :class="`hd-input--${props.variant}`"
    @input="onInput"
  >
</template>

<style scoped>
.hd-input {
  display: block;
  width: 100%;
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  background: var(--color-card);
  border: var(--border-input) solid var(--color-ink);
  border-radius: var(--r-input);
  box-shadow: inset 2px 2px 0 rgba(0, 0, 0, 0.04);
  min-height: 44px;
  box-sizing: border-box;
}
.hd-input::placeholder {
  color: var(--color-ink-muted);
  opacity: 0.7;
}
.hd-input--code {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  letter-spacing: 0.4em;
  text-align: center;
  text-transform: uppercase;
  border-style: dashed;
  border-radius: 14px;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdInput
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdInput.vue frontend/src/components/ui/__tests__/HdInput.spec.ts
git commit -m "feat(ds): add HdInput primitive (default + code variant)"
```

## Task 13: HdAvatar component

**Files:**

- Create: `frontend/src/components/ui/HdAvatar.vue`
- Test: `frontend/src/components/ui/__tests__/HdAvatar.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdAvatar.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdAvatar from "@/components/ui/HdAvatar.vue";

describe("HdAvatar", () => {
  it("renders the initial passed in", () => {
    const w = mount(HdAvatar, { props: { initial: "S", color: "var(--avatar-3)" } });
    expect(w.text()).toBe("S");
  });

  it("applies the size class", () => {
    const sm = mount(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "sm" } });
    const lg = mount(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "lg" } });
    expect(sm.classes()).toContain("hd-avatar--sm");
    expect(lg.classes()).toContain("hd-avatar--lg");
  });

  it("sets background color via inline style", () => {
    const w = mount(HdAvatar, { props: { initial: "S", color: "#FFB4A2" } });
    expect(w.attributes("style")).toContain("background");
    expect(w.attributes("style")).toContain("#FFB4A2".toLowerCase());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdAvatar
```

Expected: FAIL with "Cannot find module '@/components/ui/HdAvatar.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdAvatar.vue`:

```vue
<script setup lang="ts">
type Size = "sm" | "md" | "lg";

interface Props {
  initial: string;
  color: string;
  size?: Size;
}

const props = withDefaults(defineProps<Props>(), { size: "md" });
</script>

<template>
  <span
    class="hd-avatar"
    :class="`hd-avatar--${props.size}`"
    :style="{ background: props.color }"
    aria-hidden="true"
  >
    {{ props.initial }}
  </span>
</template>

<style scoped>
.hd-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-avatar);
  box-shadow: var(--shadow-avatar);
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
  flex-shrink: 0;
  user-select: none;
}
.hd-avatar--sm {
  width: 28px;
  height: 28px;
  font-size: 0.8rem;
}
.hd-avatar--md {
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
}
.hd-avatar--lg {
  width: 64px;
  height: 64px;
  font-size: 1.6rem;
  border-radius: 22px 28px 18px 24px;
  box-shadow: 4px 4px 0 var(--color-ink);
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdAvatar
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdAvatar.vue frontend/src/components/ui/__tests__/HdAvatar.spec.ts
git commit -m "feat(ds): add HdAvatar primitive (sm/md/lg with color + initial)"
```

## Task 14: HdTimer component

**Files:**

- Create: `frontend/src/components/ui/HdTimer.vue`
- Test: `frontend/src/components/ui/__tests__/HdTimer.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdTimer.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdTimer from "@/components/ui/HdTimer.vue";

describe("HdTimer", () => {
  it("renders the seconds value", () => {
    const w = mount(HdTimer, { props: { seconds: 42 } });
    expect(w.text()).toContain("42");
  });

  it("uses calm style above the urgentAt threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 30, urgentAt: 10 } });
    expect(w.classes()).toContain("hd-timer--calm");
    expect(w.classes()).not.toContain("hd-timer--urgent");
  });

  it("flips to urgent style at or below the urgentAt threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 7, urgentAt: 10 } });
    expect(w.classes()).toContain("hd-timer--urgent");
  });

  it("uses 10s as the default urgent threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 9 } });
    expect(w.classes()).toContain("hd-timer--urgent");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdTimer
```

Expected: FAIL with "Cannot find module '@/components/ui/HdTimer.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdTimer.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";

interface Props {
  seconds: number;
  urgentAt?: number;
}

const props = withDefaults(defineProps<Props>(), { urgentAt: 10 });

const isUrgent = computed(() => props.seconds <= props.urgentAt);
</script>

<template>
  <div
    class="hd-timer"
    :class="isUrgent ? 'hd-timer--urgent' : 'hd-timer--calm'"
    :aria-live="isUrgent ? 'assertive' : 'polite'"
  >
    {{ props.seconds }}
  </div>
</template>

<style scoped>
.hd-timer {
  display: inline-block;
  padding: 6px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 2.4rem;
  line-height: 1.05;
  border: 2.5px solid var(--color-ink);
  border-radius: 14px 22px 16px 12px;
  box-shadow: 4px 4px 0 var(--color-ink);
  min-width: 4rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
  transform: rotate(-1deg);
  transition: background-color var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out);
}
.hd-timer--calm {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink);
}
.hd-timer--urgent {
  background: var(--color-marker-red);
  color: white;
  animation: heartbeat 1s var(--ease-spring) infinite;
}
@keyframes heartbeat {
  0%, 100% { transform: rotate(-1deg) scale(1); }
  50% { transform: rotate(-1deg) scale(1.04); }
}
@media (prefers-reduced-motion: reduce) {
  .hd-timer--urgent { animation: none; }
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdTimer
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdTimer.vue frontend/src/components/ui/__tests__/HdTimer.spec.ts
git commit -m "feat(ds): add HdTimer primitive with calm/urgent threshold"
```

## Task 15: HdPill component

**Files:**

- Create: `frontend/src/components/ui/HdPill.vue`
- Test: `frontend/src/components/ui/__tests__/HdPill.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdPill.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdPill from "@/components/ui/HdPill.vue";

describe("HdPill", () => {
  it("renders default slot", () => {
    const w = mount(HdPill, { slots: { default: "ready" } });
    expect(w.text()).toBe("ready");
  });

  it("applies the default variant class", () => {
    const w = mount(HdPill, { slots: { default: "x" } });
    expect(w.classes()).toContain("hd-pill--default");
  });

  it("applies the info variant class", () => {
    const w = mount(HdPill, { props: { variant: "info" }, slots: { default: "x" } });
    expect(w.classes()).toContain("hd-pill--info");
  });

  it("applies the success variant class", () => {
    const w = mount(HdPill, { props: { variant: "success" }, slots: { default: "x" } });
    expect(w.classes()).toContain("hd-pill--success");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdPill
```

Expected: FAIL with "Cannot find module '@/components/ui/HdPill.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdPill.vue`:

```vue
<script setup lang="ts">
type Variant = "default" | "info" | "success";

interface Props {
  variant?: Variant;
}

const props = withDefaults(defineProps<Props>(), { variant: "default" });
</script>

<template>
  <span class="hd-pill" :class="`hd-pill--${props.variant}`">
    <slot />
  </span>
</template>

<style scoped>
.hd-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
  background: var(--color-card);
  box-shadow: var(--shadow-pill);
  line-height: 1.4;
}
.hd-pill--default {
  color: var(--color-ink);
}
.hd-pill--info {
  color: var(--color-ballpoint-blue);
  border-color: var(--color-ballpoint-blue);
}
.hd-pill--success {
  background: var(--color-meadow-green);
  color: var(--color-ink);
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdPill
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdPill.vue frontend/src/components/ui/__tests__/HdPill.spec.ts
git commit -m "feat(ds): add HdPill primitive (default/info/success)"
```

## Task 16: HdReactionPad component

**Files:**

- Create: `frontend/src/components/ui/HdReactionPad.vue`
- Test: `frontend/src/components/ui/__tests__/HdReactionPad.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdReactionPad.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import { REACTION_KEYS } from "@/composables/useReactions";

describe("HdReactionPad", () => {
  it("renders a button per reaction key", () => {
    const w = mount(HdReactionPad);
    expect(w.findAll("button")).toHaveLength(REACTION_KEYS.length);
  });

  it("emits 'react' with the key when a button is clicked", async () => {
    const w = mount(HdReactionPad);
    await w.findAll("button")[0]!.trigger("click");
    const emitted = w.emitted("react");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual([REACTION_KEYS[0]]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdReactionPad
```

Expected: FAIL with "Cannot find module '@/components/ui/HdReactionPad.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdReactionPad.vue`:

```vue
<script setup lang="ts">
import { REACTION_EMOJI, REACTION_KEYS, type ReactionKey } from "@/composables/useReactions";

defineEmits<{ react: [ReactionKey] }>();
</script>

<template>
  <div class="hd-rpad" role="group" aria-label="Reactions">
    <button
      v-for="k in REACTION_KEYS"
      :key="k"
      type="button"
      class="hd-rpad__btn"
      :aria-label="`React with ${k}`"
      @click="$emit('react', k)"
    >
      {{ REACTION_EMOJI[k] }}
    </button>
  </div>
</template>

<style scoped>
.hd-rpad {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}
.hd-rpad__btn {
  width: 40px;
  height: 40px;
  border-radius: 12px 16px 11px 14px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  box-shadow: 2px 2px 0 var(--color-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring), box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-rpad__btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdReactionPad
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdReactionPad.vue frontend/src/components/ui/__tests__/HdReactionPad.spec.ts
git commit -m "feat(ds): add HdReactionPad primitive (5 emoji reactions)"
```

## Task 17: HdToast component (parallel to existing ToastContainer)

The existing toast system stays in place; we add a parallel `HdToast` that consumes the same notifications composable but renders in the new style. Migration of all callers happens in Sprint 1.

**Files:**

- Create: `frontend/src/components/ui/HdToast.vue`
- Test: `frontend/src/components/ui/__tests__/HdToast.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdToast.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

const notifications = [
  { id: "1", message: "Saved", type: "success" as const },
  { id: "2", message: "Failed", type: "error" as const },
];

vi.mock("@/composables/notifications", () => ({
  useNotifications: () => ({ notifications }),
}));

import HdToast from "@/components/ui/HdToast.vue";

describe("HdToast", () => {
  it("renders one toast per active notification", () => {
    const w = mount(HdToast);
    const items = w.findAll(".hd-toast");
    expect(items).toHaveLength(2);
    expect(w.text()).toContain("Saved");
    expect(w.text()).toContain("Failed");
  });

  it("applies a type class per notification", () => {
    const w = mount(HdToast);
    const items = w.findAll(".hd-toast");
    expect(items[0]!.classes()).toContain("hd-toast--success");
    expect(items[1]!.classes()).toContain("hd-toast--error");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdToast
```

Expected: FAIL with "Cannot find module '@/components/ui/HdToast.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdToast.vue`:

```vue
<script setup lang="ts">
import { useNotifications } from "@/composables/notifications";

const { notifications } = useNotifications();
</script>

<template>
  <div class="hd-toast-stack" aria-live="polite">
    <div
      v-for="n in notifications"
      :key="n.id"
      class="hd-toast"
      :class="`hd-toast--${n.type}`"
      role="status"
    >
      {{ n.message }}
    </div>
  </div>
</template>

<style scoped>
.hd-toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
  pointer-events: none;
}
.hd-toast {
  pointer-events: auto;
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  border-radius: 14px 18px 12px 16px;
  box-shadow: var(--shadow-card);
  max-width: 320px;
}
.hd-toast--success { background: var(--color-meadow-green); }
.hd-toast--error { background: var(--color-marker-red); color: white; }
.hd-toast--info { background: var(--color-highlighter-yellow); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdToast
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdToast.vue frontend/src/components/ui/__tests__/HdToast.spec.ts
git commit -m "feat(ds): add HdToast primitive (parallel to existing ToastContainer)"
```

## Task 18: HdDialog component (parallel to existing ConfirmDialog)

**Files:**

- Create: `frontend/src/components/ui/HdDialog.vue`
- Test: `frontend/src/components/ui/__tests__/HdDialog.spec.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdDialog.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdDialog from "@/components/ui/HdDialog.vue";

describe("HdDialog", () => {
  it("renders title and message", () => {
    const w = mount(HdDialog, {
      props: { open: true, title: "Are you sure?", message: "This will leave the room." },
    });
    expect(w.text()).toContain("Are you sure?");
    expect(w.text()).toContain("This will leave the room.");
  });

  it("emits confirm when the confirm button is clicked", async () => {
    const w = mount(HdDialog, { props: { open: true, title: "T", message: "M" } });
    await w.find('[data-testid="hd-dialog-confirm"]').trigger("click");
    expect(w.emitted("confirm")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("emits cancel when the cancel button is clicked", async () => {
    const w = mount(HdDialog, { props: { open: true, title: "T", message: "M" } });
    await w.find('[data-testid="hd-dialog-cancel"]').trigger("click");
    expect(w.emitted("cancel")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("uses custom button labels when provided", () => {
    const w = mount(HdDialog, {
      props: {
        open: true,
        title: "T",
        message: "M",
        confirmLabel: "Yep",
        cancelLabel: "Nope",
      },
    });
    expect(w.find('[data-testid="hd-dialog-confirm"]').text()).toBe("Yep");
    expect(w.find('[data-testid="hd-dialog-cancel"]').text()).toBe("Nope");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdDialog
```

Expected: FAIL with "Cannot find module '@/components/ui/HdDialog.vue'".

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdDialog.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from "vue";

import HdButton from "@/components/ui/HdButton.vue";

interface Props {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
}

const props = withDefaults(defineProps<Props>(), {
  message: "",
  confirmLabel: "Confirm",
  cancelLabel: "Cancel",
  variant: "danger",
});

const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ confirm: []; cancel: [] }>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  open,
  (isOpen) => {
    const el = dialogRef.value;
    if (!el) return;
    if (isOpen && !el.open) el.showModal();
    else if (!isOpen && el.open) el.close();
  },
  { flush: "post" },
);

function onConfirm(): void {
  open.value = false;
  emit("confirm");
}

function onCancel(): void {
  open.value = false;
  emit("cancel");
}
</script>

<template>
  <dialog ref="dialogRef" class="hd-dialog" @click.self="onCancel" @close="onCancel">
    <h2 class="hd-dialog__title">{{ props.title }}</h2>
    <p v-if="props.message" class="hd-dialog__message">{{ props.message }}</p>
    <div class="hd-dialog__actions">
      <HdButton
        variant="secondary"
        data-testid="hd-dialog-cancel"
        @click="onCancel"
      >
        {{ props.cancelLabel }}
      </HdButton>
      <HdButton
        :variant="props.variant === 'danger' ? 'primary' : 'success'"
        data-testid="hd-dialog-confirm"
        @click="onConfirm"
      >
        {{ props.confirmLabel }}
      </HdButton>
    </div>
  </dialog>
</template>

<style scoped>
.hd-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  padding: 24px;
  margin: 0;
  max-width: 420px;
  width: calc(100% - 32px);
}
.hd-dialog::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}
.hd-dialog__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0 0 8px;
}
.hd-dialog__message {
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  margin: 0 0 20px;
  color: var(--color-ink-muted);
}
.hd-dialog__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd frontend && pnpm test:unit -- ui/HdDialog
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdDialog.vue frontend/src/components/ui/__tests__/HdDialog.spec.ts
git commit -m "feat(ds): add HdDialog primitive (parallel to existing ConfirmDialog)"
```

## Task 19: Design-system demo route at /__ds

**Files:**

- Create: `frontend/src/views/DesignSystemView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add the route**

Edit `frontend/src/router/index.ts` to insert a new route entry **before** the catch-all `pathMatch` entry:

```ts
import { createRouter, createWebHistory } from "vue-router";

import { normalizeRoomCode } from "@/shared/roomCode";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
    {
      path: "/rooms/:roomCode",
      name: "room",
      component: () => import("@/views/RoomView.vue"),
      beforeEnter: (to) => {
        const raw = String(to.params.roomCode || "");
        const code = normalizeRoomCode(raw);
        if (raw !== code) {
          return { name: "room", params: { roomCode: code } };
        }
        return true;
      },
    },
    {
      path: "/__ds",
      name: "design-system",
      component: () => import("@/views/DesignSystemView.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

export default router;
```

- [ ] **Step 2: Create the view**

Create `frontend/src/views/DesignSystemView.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import HdTimer from "@/components/ui/HdTimer.vue";
import HdToast from "@/components/ui/HdToast.vue";
import { AVATAR_COLORS, getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useReactions, type ReactionKey } from "@/composables/useReactions";
import { useSound, SOUND_KEYS, type SoundKey } from "@/composables/useSound";

const inputValue = ref("");
const codeValue = ref("A7KQ92");
const dialogOpen = ref(false);
const timerSeconds = ref(42);

const { enabled: soundEnabled, play } = useSound();
const reactions = useReactions();

const samplePlayers = ["simon", "maya", "jules", "anya", "rio", "kai"];
const playerSwatches = computed(() =>
  samplePlayers.map((name) => ({
    name,
    initial: getAvatarInitial(name),
    color: getAvatarColor(name),
  })),
);

const counts = computed(() => reactions.countsFor("demo"));

function onReact(k: ReactionKey): void {
  reactions.add("demo", k);
}

function playSound(k: SoundKey): void {
  play(k);
}

const soundKeys = Object.keys(SOUND_KEYS) as SoundKey[];

function setTheme(t: "light" | "dark" | null): void {
  const root = document.documentElement;
  if (t === null) root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", t);
}
</script>

<template>
  <div class="ds-page">
    <header class="ds-header">
      <h1>Design system · v1</h1>
      <div class="ds-header__actions">
        <HdButton variant="ghost" @click="setTheme('light')">Light</HdButton>
        <HdButton variant="ghost" @click="setTheme('dark')">Dark</HdButton>
        <HdButton variant="ghost" @click="setTheme(null)">System</HdButton>
      </div>
    </header>

    <section class="ds-section">
      <h2>Buttons</h2>
      <div class="ds-row">
        <HdButton variant="primary">Start a room</HdButton>
        <HdButton variant="secondary">Join with code</HdButton>
        <HdButton variant="success">Ready ✓</HdButton>
        <HdButton variant="ghost">change name</HdButton>
        <HdButton variant="primary" disabled>Disabled</HdButton>
      </div>
    </section>

    <section class="ds-section">
      <h2>Cards</h2>
      <div class="ds-row">
        <HdCard>
          <h3>Default card</h3>
          <p>Players: 4 / 10 — three are ready.</p>
        </HdCard>
        <HdCard variant="postit">
          <strong>Tip · </strong> Press Enter to add another guess.
        </HdCard>
      </div>
    </section>

    <section class="ds-section">
      <h2>Inputs</h2>
      <div class="ds-row">
        <HdInput v-model="inputValue" placeholder="your name" aria-label="Your name" />
        <HdInput v-model="codeValue" variant="code" aria-label="Room code" />
      </div>
      <p>Value: {{ inputValue }} / {{ codeValue }}</p>
    </section>

    <section class="ds-section">
      <h2>Avatars</h2>
      <div class="ds-row">
        <HdAvatar
          v-for="(p, i) in playerSwatches"
          :key="p.name"
          :initial="p.initial"
          :color="p.color"
          :size="i % 3 === 0 ? 'sm' : i % 3 === 1 ? 'md' : 'lg'"
        />
      </div>
      <p>Palette tokens: {{ AVATAR_COLORS.join(', ') }}</p>
    </section>

    <section class="ds-section">
      <h2>Timer</h2>
      <div class="ds-row">
        <HdTimer :seconds="timerSeconds" />
        <HdButton variant="secondary" @click="timerSeconds = Math.max(0, timerSeconds - 5)">
          -5
        </HdButton>
        <HdButton variant="secondary" @click="timerSeconds = Math.min(99, timerSeconds + 5)">
          +5
        </HdButton>
        <HdPill variant="info">Drops to urgent at ≤ 10</HdPill>
      </div>
    </section>

    <section class="ds-section">
      <h2>Pills</h2>
      <div class="ds-row">
        <HdPill>default</HdPill>
        <HdPill variant="info">info</HdPill>
        <HdPill variant="success">ready ✓</HdPill>
      </div>
    </section>

    <section class="ds-section">
      <h2>Reactions</h2>
      <HdReactionPad @react="onReact" />
      <p>Counts: {{ counts }}</p>
    </section>

    <section class="ds-section">
      <h2>Dialog</h2>
      <HdButton variant="primary" @click="dialogOpen = true">Open dialog</HdButton>
      <HdDialog
        v-model:open="dialogOpen"
        title="Leave the room?"
        message="You'll lose your spot if the round has started."
        confirm-label="Leave"
        cancel-label="Stay"
        variant="danger"
      />
    </section>

    <section class="ds-section">
      <h2>Sound (off by default)</h2>
      <div class="ds-row">
        <HdPill :variant="soundEnabled ? 'success' : 'default'">
          {{ soundEnabled ? 'on' : 'off' }}
        </HdPill>
        <HdButton variant="secondary" @click="soundEnabled = !soundEnabled">
          Toggle
        </HdButton>
        <HdButton
          v-for="k in soundKeys"
          :key="k"
          variant="ghost"
          @click="playSound(k)"
        >
          {{ k }}
        </HdButton>
      </div>
      <p>No sound files ship in Sprint 0; clicks are no-ops if files 404.</p>
    </section>

    <HdToast />
  </div>
</template>

<style scoped>
.ds-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 96px;
  position: relative;
  z-index: 1;
}
.ds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px dashed var(--color-ink);
}
.ds-header__actions {
  display: flex;
  gap: 8px;
}
.ds-section {
  margin-bottom: 40px;
}
.ds-section h2 {
  margin: 0 0 16px;
}
.ds-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
```

- [ ] **Step 3: Verify the route loads**

Run:

```bash
cd frontend && pnpm dev
```

Open `http://localhost:5173/__ds` in a browser. Expect the demo page rendering every primitive on cream paper. Click each button, toggle theme buttons, open the dialog, click reactions — verify state updates.

Verify:

- All buttons have visible focus rings on Tab key
- Dark mode toggle changes background to dark
- Timer below 10 turns red and pulses
- Reactions counts update on click
- Dialog opens, closes via cancel/confirm/backdrop
- No console errors

`Ctrl+C` to stop.

- [ ] **Step 4: Type-check**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/views/DesignSystemView.vue
git commit -m "feat(ds): add /__ds demo route showing every primitive"
```

## Task 20: Add sounds placeholder directory

The `useSound` composable references files at `/sounds/*.ogg`. We don't ship audio in Sprint 0 (Sprint 2 wires real sounds), but we add the directory so it exists.

**Files:**

- Create: `frontend/public/sounds/.gitkeep`

- [ ] **Step 1: Create the directory placeholder**

Run:

```bash
mkdir -p frontend/public/sounds && touch frontend/public/sounds/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add frontend/public/sounds/.gitkeep
git commit -m "chore(ds): reserve frontend/public/sounds/ for Sprint 2 audio"
```

## Task 21: Run the full check suite

This sprint should leave the build green. Run all checks and confirm.

- [ ] **Step 1: Run unit tests**

Run:

```bash
cd frontend && pnpm test:unit
```

Expected: ALL PASS — including the new `Hd*` and `use*` tests added in this sprint, plus the pre-existing tests for `RoomCodeInput`, `LocaleSelector`, `CreateJoinCard`, `PlayerListPanel`, etc. (no existing test should fail because no existing code was modified semantically).

If any pre-existing test fails because it depended on a CSS variable that changed (e.g. `--color-primary`), update the assertion to use the new token name. Do NOT silence or skip a test.

- [ ] **Step 2: Run type-check**

Run:

```bash
cd frontend && pnpm type-check
```

Expected: passes.

- [ ] **Step 3: Run lint/format check**

Run:

```bash
cd frontend && pnpm lint
```

Expected: passes. If formatting issues appear in new files, run `pnpm format` to auto-fix and re-commit.

- [ ] **Step 4: Run build**

Run:

```bash
cd frontend && pnpm build
```

Expected: build succeeds. Note the bundle-size output. Acceptable: + ~120 KB gzipped (fonts + howler + motion + html-to-image). If it's much larger, investigate with `pnpm dlx vite-bundle-visualizer` before proceeding to Sprint 1.

- [ ] **Step 5: Commit any auto-formatting fixes if needed**

```bash
git status
git add -p   # review and stage any formatting fixes
git commit -m "chore(ds): apply biome formatting to design-system files"
```

If `git status` is clean, skip this step.

## Task 22: Manual visual QA on /__ds

This is a checkpoint, not a code change. Verify visually that the design system meets the spec's acceptance criteria for Sprint 0.

- [ ] **Step 1: Run dev server and load the demo**

Run:

```bash
cd frontend && pnpm dev
```

Open `http://localhost:5173/__ds` in Chrome.

- [ ] **Step 2: Light-mode contrast check**

Click "Light" in the demo header. Open Chrome DevTools → Lighthouse → run Accessibility audit on the page. Confirm:

- No "contrast" failures.
- Focus order is logical when pressing Tab.

- [ ] **Step 3: Dark-mode contrast check**

Click "Dark" in the demo header. Re-run Lighthouse Accessibility audit. Confirm same.

- [ ] **Step 4: Reduced-motion check**

In DevTools → Rendering panel → "Emulate CSS media feature prefers-reduced-motion" → Reduce. Reload `/__ds`. Confirm:

- The urgent timer no longer pulses.
- Buttons still respond to press visually (color/state) but without motion.

- [ ] **Step 5: Mobile width check**

Resize the viewport to 375 px wide. Confirm:

- All sections wrap without horizontal scroll.
- Touch targets remain ≥ 44 × 44 px (use DevTools to inspect button heights).
- Reaction pad wraps to multiple rows if needed.

- [ ] **Step 6: Stop the dev server**

`Ctrl+C` to stop.

- [ ] **Step 7: Commit a CHECKLIST file noting the QA pass**

This is optional but useful for the next sprint to know foundations are validated. Skip if undesired.

```bash
# No code change — Sprint 0 is complete.
```

---

## Sprint 0 acceptance check

Re-read §10 of the spec ([docs/superpowers/specs/2026-04-18-ui-redesign-2026-design.md:344-355](../specs/2026-04-18-ui-redesign-2026-design.md)). For each criterion, verify:

1. ✅ **Tokens-only UI** — every `Hd*` component uses CSS custom properties from `tokens.css`. Verified by code review.
2. ✅ **WCAG AA contrast (light + dark)** — verified via Lighthouse on `/__ds` in Task 22.
3. ✅ **Visible focus rings, keyboard reachability** — universal `:focus-visible` rule in `main.css`; tested in Task 22.
4. ✅ **Reduced motion respected** — `useSound`/`HdTimer`/transitions all gated; tested in Task 22.
5. ✅ **375 / 768 / 1024 / 1440 px verified** — partial (mobile + desktop width verified on `/__ds`); full per-screen verification happens in Sprints 1–4.
6. ✅ **No emoji in structural UI** — only inside `HdReactionPad`.
7. ✅ **Sprint features end-to-end** — N/A (Sprint 0 has no user-facing features beyond the demo route).
8. ✅ **Existing test suite passes** — verified in Task 21.

If any criterion fails, return to the relevant task and fix before declaring Sprint 0 complete.

## Hand-off to Sprint 1

Sprint 1 (Home + Lobby) will:

- Replace the old `CreateJoinCard`, `HomePlayerPreferences`, `HowToPlay`, `RoomCodeInput`, `NamePromptDialog` with new compositions of `Hd*` primitives.
- Migrate `ToastContainer` callers to `HdToast`; migrate `ConfirmDialog` callers to `HdDialog`; delete the old components.
- Add backend `quick-play` endpoint and `color` field on player.
- Add the `useAvatar` colour to the player identity flow (persisted via existing Pinia store).

The Sprint 1 plan is written separately at `docs/superpowers/plans/2026-MM-DD-ui-redesign-sprint-1-home-lobby.md` when ready to execute.
