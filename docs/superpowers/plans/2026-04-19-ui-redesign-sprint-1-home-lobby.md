# UI Redesign · Sprint 1 — Home + Lobby + Settings Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Home and Lobby screens on top of Sprint 0's design system; introduce a global settings panel (gear icon → sidepanel with identity/locale/theme/sound/about); add player avatar colours and anonymous quick-play end-to-end.

**Architecture:** Three new primitives (`HdIconButton`, `HdSegmented`, `HdSidepanel`) extend the existing `Hd*` set. A `useTheme` composable owns theme persistence and the `<html data-theme>` attribute. A `SettingsPanel.vue` composite mounts globally in `App.vue` so the gear icon is reachable from every screen. Home and Lobby views are rewritten from scratch against the new primitives — identity moves to the settings panel, quick-play becomes a one-tap action, avatars surface in the player list. Backend gains a `color` field on Player and a `/api/rooms/quick-play` endpoint.

**Tech Stack:** Continues Sprint 0 stack — Vue 3, Vite, Tailwind 4, TypeScript, Vitest, `@vue/test-utils`, Pinia (with `pinia-plugin-persistedstate`), vue-i18n, FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest.

---

## Source-of-truth references

- Design spec: [docs/superpowers/specs/2026-04-18-ui-redesign-2026-design.md](../specs/2026-04-18-ui-redesign-2026-design.md). §6.1 (Home), §6.2 (Lobby), §6.7 (Settings panel) are the primary sections for this sprint. §5 lists every primitive's variants. §7's "Feature integration map" row for "Settings panel" explicitly calls out the new components.
- Sprint 0 plan: [docs/superpowers/plans/2026-04-18-ui-redesign-sprint-0-foundations.md](./2026-04-18-ui-redesign-sprint-0-foundations.md). Contains the conventions (TDD per task, lefthook hooks run on commit, commit-message style `feat(ds):`, tests use vitest 4 / `@vue/test-utils`).
- Existing implementations being replaced: [frontend/src/views/HomeView.vue](../../../frontend/src/views/HomeView.vue), [frontend/src/views/LobbyView.vue](../../../frontend/src/views/LobbyView.vue), [frontend/src/views/RoomView.vue](../../../frontend/src/views/RoomView.vue), [frontend/src/components/CreateJoinCard.vue](../../../frontend/src/components/CreateJoinCard.vue), [frontend/src/components/HomePlayerPreferences.vue](../../../frontend/src/components/HomePlayerPreferences.vue), [frontend/src/components/PlayerListPanel.vue](../../../frontend/src/components/PlayerListPanel.vue), [frontend/src/components/RoomCodeInput.vue](../../../frontend/src/components/RoomCodeInput.vue), [frontend/src/components/NamePromptDialog.vue](../../../frontend/src/components/NamePromptDialog.vue), [frontend/src/components/HowToPlay.vue](../../../frontend/src/components/HowToPlay.vue).
- Legacy UI primitives being retired: [frontend/src/components/ConfirmDialog.vue](../../../frontend/src/components/ConfirmDialog.vue) (→ `HdDialog`), [frontend/src/components/ToastContainer.vue](../../../frontend/src/components/ToastContainer.vue) (→ `HdToast`).

## File structure

### Files created

|Path|Responsibility|
|---|---|
|`frontend/src/components/ui/HdIconButton.vue`|Icon-only button with visually-hidden text label; `default` + `ghost` variants.|
|`frontend/src/components/ui/HdSegmented.vue`|Generic segmented radio control (N options); used by theme picker.|
|`frontend/src/components/ui/HdSidepanel.vue`|Slide-in right panel (desktop) / bottom sheet (mobile); focus-trap, scrim, Escape + backdrop close.|
|`frontend/src/composables/useTheme.ts`|Light / Dark / Auto state, persisted to `localStorage` key `ds:theme`, applies `data-theme` on `<html>`.|
|`frontend/src/components/settings/SettingsPanel.vue`|Composite: identity (name + colour picker), locale, theme segmented, sound toggle, about links.|
|`frontend/src/components/settings/AvatarColorPicker.vue`|6-swatch picker built on `HdAvatar` primitives.|
|`frontend/src/components/home/HomeCreateJoin.vue`|New Home body: Start / Find random / room code + Join / Quick-play.|
|`frontend/src/components/home/HowToPlayDialog.vue`|Short `HdDialog`-wrapped "how to play" (replaces old collapsible).|
|`frontend/src/components/lobby/LobbyTopbar.vue`|Leave button + yellow room-code chip + copy affordance + gear icon row.|
|`frontend/src/components/lobby/LobbyPlayerList.vue`|Avatar + name + role badge rows.|
|`frontend/src/components/lobby/LobbyGameSettings.vue`|Inline collapsible difficulty / rounds / drawing time / guessing time (rewrites `GameSettingsPanel.vue`).|
|`frontend/src/components/ui/__tests__/HdIconButton.spec.ts`|Smoke + a11y-label + click tests.|
|`frontend/src/components/ui/__tests__/HdSegmented.spec.ts`|Smoke + selection + emit tests.|
|`frontend/src/components/ui/__tests__/HdSidepanel.spec.ts`|Open/close + backdrop + escape + focus-trap smoke.|
|`frontend/src/composables/__tests__/useTheme.spec.ts`|Persistence + data-theme application.|
|`frontend/src/components/settings/__tests__/SettingsPanel.spec.ts`|Rendering, propagation to composables/store.|
|`frontend/src/components/home/__tests__/HomeCreateJoin.spec.ts`|Migrates + extends the old `CreateJoinCard.spec.ts` for the new component.|
|`backend/app/rooms/schemas.py`|**Modify** — add `color` to `PlayerStateSchema` and `QuickPlayResponseSchema` (see §Backend).|
|`backend/app/players/models.py` or equivalent|**Modify** — add `color: Mapped[str \|None]` to `Player`.|
|`backend/alembic/versions/<timestamp>_add_player_color.py`|New Alembic migration.|
|`backend/app/rooms/router.py`|**Modify** — add `POST /rooms/quick-play`.|

### Files modified

|Path|Change|
|---|---|
|`frontend/src/App.vue`|Mount global `SettingsPanel` + gear button; provide `useTheme` at app root.|
|`frontend/src/views/HomeView.vue`|Rewrite as compositions of new primitives + `HomeCreateJoin`.|
|`frontend/src/views/LobbyView.vue`|Rewrite as compositions of new primitives + `LobbyTopbar` / `LobbyPlayerList` / `LobbyGameSettings` + existing `SharedDrawpad` re-skinned.|
|`frontend/src/views/RoomView.vue`|Keep the routing shell; update toast + confirm-dialog callers to use `HdToast` / `HdDialog`.|
|`frontend/src/stores/game.ts`|Add `localPlayerColor` field; persist via `pinia-plugin-persistedstate`.|
|`frontend/src/lib/api.ts`|Add typed wrapper for `POST /rooms/quick-play` via generated Zod schema.|
|`frontend/src/i18n` locales|Add keys for the new panel + about section; remove keys for deleted components.|
|`frontend/src/views/__tests__/HomeView.spec.ts`|Rewrite to cover new Home composition.|
|`frontend/src/views/__tests__/RoomView.spec.ts`|Update for gear icon + new Lobby composition.|
|`frontend/src/components/__tests__/*.spec.ts`|Delete tests for deleted components; migrate/retain those that still cover live code.|
|`contracts/openapi.json`|Regenerate via `pnpm contracts:generate`.|
|`contracts/room-events.json`|Regenerate (Player gains `color`).|
|`frontend/src/generated/api.ts`|Regenerated Zod + types from the OpenAPI doc.|

### Files deleted (after their replacements ship and callers migrate)

- `frontend/src/components/CreateJoinCard.vue` + spec → `HomeCreateJoin.vue`
- `frontend/src/components/HomePlayerPreferences.vue` → absorbed into `SettingsPanel`
- `frontend/src/components/HowToPlay.vue` → `HowToPlayDialog.vue`
- `frontend/src/components/NamePromptDialog.vue` → name editing lives in `SettingsPanel`
- `frontend/src/components/RoomCodeInput.vue` + spec → inlined in `HomeCreateJoin` using `HdInput` `code` variant
- `frontend/src/components/ConfirmDialog.vue` → `HdDialog`
- `frontend/src/components/ToastContainer.vue` → `HdToast`
- `frontend/src/components/GameSettingsPanel.vue` → `LobbyGameSettings.vue`
- `frontend/src/components/PlayerListPanel.vue` → `LobbyPlayerList.vue`

## Conventions for this sprint

- Strict TDD on new primitives (Tasks 1–3) and on `useTheme` (Task 4). Failing test → impl → passing test → commit.
- Rebuild tasks (Home, Lobby) migrate existing tests: start by updating the test file to reflect the new expected DOM, watch it fail against the old view, then rewrite the view until it passes. Delete old component specs only in the explicit deletion task.
- Keep the `Hd*` primitives stateless — new composables own cross-cutting state.
- Every screen must have `SettingsPanel` reachable; verify on at least Home and Lobby during this sprint.
- Avatar colour is assigned server-side on join if the client didn't send one; client may override by sending a preferred colour in the join payload. Colour is one of `avatar-1` … `avatar-6` (string token name, not hex).
- Backend: single Alembic migration, no data backfill required (existing rows get `NULL` and the server assigns on first join).
- Keep commit messages conventional: `feat(ds):` / `feat(frontend):` / `feat(backend):` / `chore(frontend):` / `test(backend):` as appropriate to the scope.

---

## Task 1: HdIconButton primitive

**Files:**

- Create: `frontend/src/components/ui/HdIconButton.vue`
- Test: `frontend/src/components/ui/__tests__/HdIconButton.spec.ts`

Icon-only button for gear, leave arrow, close X, copy, etc. Renders a `<button>` with the visually-hidden label set from a required `label` prop, and a slotted icon visible to sighted users. Two variants: `default` (hand-drawn chip with offset shadow like `HdButton`) and `ghost` (transparent, subtle hover).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdIconButton.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdIconButton from "@/components/ui/HdIconButton.vue";

describe("HdIconButton", () => {
  it("renders a button with the label as aria-label", () => {
    const w = mount(HdIconButton, { props: { label: "Settings" }, slots: { default: "⚙" } });
    expect(w.element.tagName).toBe("BUTTON");
    expect(w.attributes("aria-label")).toBe("Settings");
    expect(w.attributes("type")).toBe("button");
  });

  it("renders the slotted icon content", () => {
    const w = mount(HdIconButton, {
      props: { label: "Close" },
      slots: { default: "<svg data-testid='x'></svg>" },
    });
    expect(w.find("[data-testid='x']").exists()).toBe(true);
  });

  it("emits click when pressed and not disabled", async () => {
    const w = mount(HdIconButton, { props: { label: "X" }, slots: { default: "x" } });
    await w.trigger("click");
    expect(w.emitted("click")).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = mount(HdIconButton, { props: { label: "X", disabled: true }, slots: { default: "x" } });
    await w.trigger("click");
    expect(w.emitted("click")).toBeUndefined();
  });

  it("applies the ghost variant class", () => {
    const w = mount(HdIconButton, {
      props: { label: "X", variant: "ghost" },
      slots: { default: "x" },
    });
    expect(w.classes()).toContain("hd-icon-btn--ghost");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from the worktree:

```bash
cd /Users/simon/code/personal/6-second-scribbles/.worktrees/redesign-sprint-0/frontend
pnpm test:unit -- HdIconButton
```

Expected: FAIL with `Cannot find module '@/components/ui/HdIconButton.vue'`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdIconButton.vue`:

```vue
<script setup lang="ts">
type Variant = "default" | "ghost";

interface Props {
  label: string;
  variant?: Variant;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "default",
  disabled: false,
});

defineEmits<{ click: [MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="hd-icon-btn"
    :class="`hd-icon-btn--${props.variant}`"
    :aria-label="props.label"
    :disabled="props.disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.hd-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--r-pill);
  cursor: pointer;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-icon-btn--default {
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  box-shadow: var(--shadow-pill);
  transform: rotate(-1deg);
}
.hd-icon-btn--default:active:not(:disabled) {
  transform: rotate(-1deg) translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
.hd-icon-btn--ghost {
  background: transparent;
  color: var(--color-ink);
  border: 0;
  box-shadow: none;
}
.hd-icon-btn--ghost:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
}
.hd-icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.hd-icon-btn :slotted(svg) {
  width: 20px;
  height: 20px;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test:unit -- HdIconButton
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdIconButton.vue frontend/src/components/ui/__tests__/HdIconButton.spec.ts
git commit -m "feat(ds): add HdIconButton primitive (default + ghost)"
```

## Task 2: HdSegmented primitive

**Files:**

- Create: `frontend/src/components/ui/HdSegmented.vue`
- Test: `frontend/src/components/ui/__tests__/HdSegmented.spec.ts`

Generic segmented radio control. Takes an array of `{ value: string; label: string }` options + a v-model string. Emits `update:modelValue` when selection changes. Uses real `<input type="radio">` elements for keyboard + screen-reader support, styled as horizontal connected buttons.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdSegmented.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdSegmented from "@/components/ui/HdSegmented.vue";

const options = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "auto", label: "Auto" },
];

describe("HdSegmented", () => {
  it("renders one radio input per option with a visible label", () => {
    const w = mount(HdSegmented, { props: { modelValue: "light", options } });
    expect(w.findAll('input[type="radio"]')).toHaveLength(3);
    expect(w.text()).toContain("Light");
    expect(w.text()).toContain("Dark");
    expect(w.text()).toContain("Auto");
  });

  it("checks the radio matching modelValue", () => {
    const w = mount(HdSegmented, { props: { modelValue: "dark", options } });
    const radios = w.findAll('input[type="radio"]');
    expect((radios[0]?.element as HTMLInputElement).checked).toBe(false);
    expect((radios[1]?.element as HTMLInputElement).checked).toBe(true);
  });

  it("emits update:modelValue when a different option is selected", async () => {
    const w = mount(HdSegmented, { props: { modelValue: "light", options } });
    await w.findAll('input[type="radio"]')[2]?.setValue(true);
    expect(w.emitted("update:modelValue")?.[0]).toEqual(["auto"]);
  });

  it("groups the radios under a single name so only one is selected at a time", () => {
    const w = mount(HdSegmented, { props: { modelValue: "light", options, name: "theme" } });
    for (const r of w.findAll('input[type="radio"]')) {
      expect(r.attributes("name")).toBe("theme");
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- HdSegmented
```

Expected: FAIL `Cannot find module '@/components/ui/HdSegmented.vue'`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdSegmented.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";

interface Option {
  value: string;
  label: string;
}

interface Props {
  modelValue: string;
  options: Option[];
  name?: string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  name: undefined,
  ariaLabel: undefined,
});

const emit = defineEmits<{ "update:modelValue": [string] }>();

// Fallback group name if not supplied — stable within the component lifetime.
const groupName = computed(() => props.name ?? `hd-seg-${(Math.random() * 1e6) | 0}`);

function onChange(value: string): void {
  emit("update:modelValue", value);
}
</script>

<template>
  <div class="hd-seg" role="radiogroup" :aria-label="props.ariaLabel">
    <label
      v-for="opt in props.options"
      :key="opt.value"
      class="hd-seg__item"
      :class="{ 'hd-seg__item--active': opt.value === props.modelValue }"
    >
      <input
        type="radio"
        class="hd-seg__input"
        :name="groupName"
        :value="opt.value"
        :checked="opt.value === props.modelValue"
        @change="onChange(opt.value)"
      />
      <span class="hd-seg__label">{{ opt.label }}</span>
    </label>
  </div>
</template>

<style scoped>
.hd-seg {
  display: inline-flex;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  overflow: hidden;
  background: var(--color-card);
}
.hd-seg__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  min-height: 36px;
}
.hd-seg__item + .hd-seg__item {
  border-left: 1.5px solid var(--color-ink);
}
.hd-seg__input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.hd-seg__item--active {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.hd-seg__item:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test:unit -- HdSegmented
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdSegmented.vue frontend/src/components/ui/__tests__/HdSegmented.spec.ts
git commit -m "feat(ds): add HdSegmented primitive (radio-based segmented control)"
```

## Task 3: HdSidepanel primitive

**Files:**

- Create: `frontend/src/components/ui/HdSidepanel.vue`
- Test: `frontend/src/components/ui/__tests__/HdSidepanel.spec.ts`

Slide-in right panel on desktop, bottom sheet on mobile. Uses the native `<dialog>` element so the browser handles focus trap + Escape for free (same pattern `HdDialog` uses). v-model driven via `open` prop. Emits `close`. Renders a header with title + close `HdIconButton`, and a default slot for body content.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/HdSidepanel.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import HdSidepanel from "@/components/ui/HdSidepanel.vue";

describe("HdSidepanel", () => {
  it("renders the title and body slot", () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "Settings" },
      slots: { default: "<p>body content</p>" },
    });
    expect(w.text()).toContain("Settings");
    expect(w.text()).toContain("body content");
  });

  it("emits close + update:open=false when the close button is clicked", async () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "X" },
      slots: { default: "x" },
    });
    await w.find('[data-testid="hd-sidepanel-close"]').trigger("click");
    expect(w.emitted("close")).toHaveLength(1);
    expect(w.emitted("update:open")?.[0]).toEqual([false]);
  });

  it("calls showModal / close on the underlying dialog when open changes", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
    const w = mount(HdSidepanel, {
      props: { open: false, title: "X" },
      slots: { default: "x" },
    });
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();
    await w.setProps({ open: true });
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
    await w.setProps({ open: false });
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);
  });

  it("applies the bottom variant class", () => {
    const w = mount(HdSidepanel, {
      props: { open: true, title: "X", side: "bottom" },
      slots: { default: "x" },
    });
    expect(w.find("dialog").classes()).toContain("hd-sidepanel--bottom");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- HdSidepanel
```

Expected: FAIL `Cannot find module '@/components/ui/HdSidepanel.vue'`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ui/HdSidepanel.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from "vue";

import HdIconButton from "@/components/ui/HdIconButton.vue";

interface Props {
  title: string;
  side?: "right" | "bottom";
}

const props = withDefaults(defineProps<Props>(), { side: "right" });

const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ close: [] }>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  open,
  (v) => {
    const el = dialogRef.value;
    if (!el) return;
    if (v && !el.open) el.showModal();
    else if (!v && el.open) el.close();
  },
  { flush: "post" },
);

function onClose(): void {
  open.value = false;
  emit("close");
}

function onBackdropClick(e: MouseEvent): void {
  // Clicks on the dialog element itself (not its children) are backdrop clicks.
  if (e.target === dialogRef.value) onClose();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="hd-sidepanel"
    :class="`hd-sidepanel--${props.side}`"
    @click="onBackdropClick"
    @close="onClose"
  >
    <header class="hd-sidepanel__header">
      <h2 class="hd-sidepanel__title">{{ props.title }}</h2>
      <HdIconButton
        label="Close"
        variant="ghost"
        data-testid="hd-sidepanel-close"
        @click="onClose"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </HdIconButton>
    </header>
    <div class="hd-sidepanel__body">
      <slot />
    </div>
  </dialog>
</template>

<style scoped>
.hd-sidepanel {
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  box-shadow: var(--shadow-card);
  margin: 0;
  padding: 0;
  max-width: 100vw;
  max-height: 100vh;
}
.hd-sidepanel::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}
.hd-sidepanel--right {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: min(360px, 100vw);
  border-radius: 18px 0 0 22px;
}
.hd-sidepanel--bottom {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  top: auto;
  width: 100vw;
  max-height: 85vh;
  border-radius: 22px 22px 0 0;
}
.hd-sidepanel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1.5px dashed var(--color-ink);
}
.hd-sidepanel__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
}
.hd-sidepanel__body {
  padding: 20px;
  overflow-y: auto;
}
@media (max-width: 640px) {
  .hd-sidepanel--right {
    /* On narrow screens, a "right" side panel becomes a bottom sheet. */
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    top: auto;
    width: 100vw;
    height: auto;
    max-height: 85vh;
    border-radius: 22px 22px 0 0;
  }
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test:unit -- HdSidepanel
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/HdSidepanel.vue frontend/src/components/ui/__tests__/HdSidepanel.spec.ts
git commit -m "feat(ds): add HdSidepanel primitive (right panel / bottom sheet)"
```

## Task 4: useTheme composable

**Files:**

- Create: `frontend/src/composables/useTheme.ts`
- Test: `frontend/src/composables/__tests__/useTheme.spec.ts`

Owns the current theme (`"light"` | `"dark"` | `"auto"`) and applies it to `<html data-theme>` (empty attribute removed when auto). Persisted to `localStorage` key `ds:theme`. Follows the same `customRef` + synchronous-write pattern as `useSound` to avoid async watcher races.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/composables/__tests__/useTheme.spec.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";

describe("useTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    vi.resetModules();
  });

  it("defaults to auto and removes data-theme from <html>", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    expect(theme.value).toBe("auto");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("persists light / dark to localStorage and sets data-theme", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    theme.value = "light";
    expect(localStorage.getItem("ds:theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    theme.value = "dark";
    expect(localStorage.getItem("ds:theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("clears data-theme when switched back to auto", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    theme.value = "dark";
    theme.value = "auto";
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    expect(localStorage.getItem("ds:theme")).toBe("auto");
  });

  it("restores from localStorage on module reload", async () => {
    localStorage.setItem("ds:theme", "dark");
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    expect(theme.value).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- useTheme
```

Expected: FAIL `Cannot find module '@/composables/useTheme'`.

- [ ] **Step 3: Implement the composable**

Create `frontend/src/composables/useTheme.ts`:

```ts
import { customRef } from "vue";

export type Theme = "light" | "dark" | "auto";

const STORAGE_KEY = "ds:theme";

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "auto") return v;
  } catch {
    /* localStorage unavailable */
  }
  return "auto";
}

function writeTheme(v: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, v);
  } catch {
    /* localStorage unavailable */
  }
}

function applyTheme(v: Theme): void {
  if (typeof document === "undefined") return;
  if (v === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", v);
}

// theme is a module-level singleton: initial value is read from localStorage
// ONCE at module load. Tests that need a pre-seeded value must vi.resetModules()
// and re-import, not just write to localStorage before import.
const theme = customRef<Theme>((track, trigger) => {
  let value = readTheme();
  applyTheme(value);
  return {
    get() {
      track();
      return value;
    },
    set(next: Theme) {
      value = next;
      writeTheme(next);
      applyTheme(next);
      trigger();
    },
  };
});

export function useTheme() {
  return { theme };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test:unit -- useTheme
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useTheme.ts frontend/src/composables/__tests__/useTheme.spec.ts
git commit -m "feat(ds): add useTheme composable (light/dark/auto + localStorage)"
```

## Task 5: AvatarColorPicker component

**Files:**

- Create: `frontend/src/components/settings/AvatarColorPicker.vue`
- Test: `frontend/src/components/settings/__tests__/AvatarColorPicker.spec.ts`

A 6-swatch picker built on `HdAvatar`. Shows the current player's initial on each swatch; the selected swatch has an active ring. Emits `update:modelValue` with the chosen colour token.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/settings/__tests__/AvatarColorPicker.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import { AVATAR_COLORS } from "@/composables/useAvatar";

describe("AvatarColorPicker", () => {
  it("renders one selectable button per avatar color", () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S" },
    });
    expect(w.findAll("button")).toHaveLength(AVATAR_COLORS.length);
  });

  it("emits update:modelValue with the chosen color when clicked", async () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[0], initial: "S" },
    });
    await w.findAll("button")[2]?.trigger("click");
    expect(w.emitted("update:modelValue")?.[0]).toEqual([AVATAR_COLORS[2]]);
  });

  it("marks the current modelValue as active via aria-checked", () => {
    const w = mount(AvatarColorPicker, {
      props: { modelValue: AVATAR_COLORS[3], initial: "S" },
    });
    const btns = w.findAll("button");
    expect(btns[3]?.attributes("aria-checked")).toBe("true");
    expect(btns[0]?.attributes("aria-checked")).toBe("false");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- AvatarColorPicker
```

Expected: FAIL.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/settings/AvatarColorPicker.vue`:

```vue
<script setup lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.vue";
import { AVATAR_COLORS, type AvatarColor } from "@/composables/useAvatar";

interface Props {
  modelValue: AvatarColor;
  initial: string;
}

defineProps<Props>();
const emit = defineEmits<{ "update:modelValue": [AvatarColor] }>();

function pick(c: AvatarColor): void {
  emit("update:modelValue", c);
}
</script>

<template>
  <div class="avatar-picker" role="radiogroup" aria-label="Avatar color">
    <button
      v-for="c in AVATAR_COLORS"
      :key="c"
      type="button"
      class="avatar-picker__btn"
      :class="{ 'avatar-picker__btn--active': c === modelValue }"
      role="radio"
      :aria-checked="c === modelValue"
      @click="pick(c)"
    >
      <HdAvatar :initial="initial" :color="c" size="md" />
    </button>
  </div>
</template>

<style scoped>
.avatar-picker {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.avatar-picker__btn {
  background: transparent;
  border: 0;
  padding: 4px;
  border-radius: 14px;
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring);
}
.avatar-picker__btn--active {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.avatar-picker__btn:active {
  transform: scale(0.94);
}
</style>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pnpm test:unit -- AvatarColorPicker
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/AvatarColorPicker.vue frontend/src/components/settings/__tests__/AvatarColorPicker.spec.ts
git commit -m "feat(frontend): add AvatarColorPicker (6-swatch selector)"
```

## Task 6: game store — add localPlayerColor

**Files:**

- Modify: `frontend/src/stores/game.ts`
- Modify: `frontend/src/stores/__tests__/*` (if existing tests depend on player shape)

Add a persisted `localPlayerColor` field defaulting to a deterministic colour derived from the player id (via `getAvatarColor`). Extend `setLocalPlayer`-family setters to accept colour. Include colour in the persisted-state plugin list.

- [ ] **Step 1: Read the current store to understand shape**

Run:

```bash
sed -n '1,120p' frontend/src/stores/game.ts
```

Note the `localPlayerName`, `localPlayerLocale` patterns and the persisted-state plugin's `paths` array.

- [ ] **Step 2: Add `localPlayerColor` ref, setter, default derivation, and persisted path**

Diff-style edits inside `frontend/src/stores/game.ts`:

- Add an import near the top:

```ts
import { AVATAR_COLORS, getAvatarColor, type AvatarColor } from "@/composables/useAvatar";
```

- Add a ref after `localPlayerLocale`:

```ts
const localPlayerColor = ref<AvatarColor>(AVATAR_COLORS[0]);
```

- Inside `setLocalPlayer(id, name)` (and the `AndSave` variant), after assigning the id / name, derive and set colour if the current value is falsy or still a default:

```ts
if (!localPlayerColor.value) localPlayerColor.value = getAvatarColor(id);
```

- Add a `setLocalPlayerColor(c: AvatarColor)` setter that validates `c` is in `AVATAR_COLORS`:

```ts
function setLocalPlayerColor(c: AvatarColor): void {
  if (!AVATAR_COLORS.includes(c)) return;
  localPlayerColor.value = c;
}
```

- Export `localPlayerColor` and `setLocalPlayerColor` from the return object.
- Add `"localPlayerColor"` to the `paths` array in the persisted-state plugin config.

- [ ] **Step 3: Write/update a store test that exercises the new field**

In a new file `frontend/src/stores/__tests__/game-avatar-color.spec.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { AVATAR_COLORS, getAvatarColor } from "@/composables/useAvatar";
import { useGameStore } from "@/stores/game";

describe("game store — localPlayerColor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("defaults to a deterministic color after setLocalPlayer", () => {
    const store = useGameStore();
    store.setLocalPlayer("player-abc", "Simon");
    expect(store.localPlayerColor).toBe(getAvatarColor("player-abc"));
  });

  it("setLocalPlayerColor accepts a valid AvatarColor", () => {
    const store = useGameStore();
    store.setLocalPlayerColor(AVATAR_COLORS[2]);
    expect(store.localPlayerColor).toBe(AVATAR_COLORS[2]);
  });

  it("setLocalPlayerColor ignores invalid colors", () => {
    const store = useGameStore();
    const before = store.localPlayerColor;
    store.setLocalPlayerColor("bogus" as never);
    expect(store.localPlayerColor).toBe(before);
  });
});
```

- [ ] **Step 4: Run tests**

```bash
pnpm test:unit -- game-avatar-color
pnpm type-check
```

Expected: new test passes, type-check clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/game.ts frontend/src/stores/__tests__/game-avatar-color.spec.ts
git commit -m "feat(frontend): persist localPlayerColor in game store"
```

## Task 7: backend — Player.color field + migration

**Files:**

- Modify: player model file (`backend/app/players/models.py` or equivalent; find via `grep -rn "class Player" backend/app`).
- Create: `backend/alembic/versions/<timestamp>_add_player_color.py` via `alembic revision --autogenerate -m "add player color"`.
- Modify: `backend/app/rooms/schemas.py` — include `color: str | None` in `PlayerStateSchema`.
- Modify: any service / manager code that constructs Player records to default-assign a colour (round-robin among the six tokens based on existing players in the room, or deterministic from player id).

- [ ] **Step 1: Locate the Player model and current schema**

Run from the worktree:

```bash
grep -rn "class Player" backend/app
grep -rn "PlayerStateSchema\|PlayerSchema" backend/app
```

Read the matches to find the model + schema definitions.

- [ ] **Step 2: Add the `color` column to the Player model**

Find the Player class (likely in `backend/app/players/models.py` or `backend/app/rooms/state.py`). Add:

```python
color: Mapped[str | None] = mapped_column(String(16), nullable=True)
```

Adjust the import for `String` and `Mapped` / `mapped_column` to match the file's existing style.

- [ ] **Step 3: Generate the migration**

```bash
cd backend
uv run alembic revision --autogenerate -m "add player color"
```

Review the generated file; confirm it contains an `op.add_column("players", ...)` (or the appropriate table name) with `sa.String(16)` and `nullable=True`. Remove any unrelated diffs that may have snuck in.

- [ ] **Step 4: Add `color` to `PlayerStateSchema`**

In `backend/app/rooms/schemas.py`, find `PlayerStateSchema` (or whichever schema serialises a Player into a WebSocket / API response) and add:

```python
color: str | None = None
```

If there's a constructor/factory function, plumb the value through.

- [ ] **Step 5: Default-assign a colour on player creation**

Find the code path that creates a Player record (likely in `backend/app/rooms/manager.py` or `player_lifecycle.py`). When a Player is created without a colour supplied by the client:

```python
from app.core.avatar import AVATAR_COLOR_TOKENS  # define this constant, see Step 6

def _pick_avatar_color(player_id: str, existing_colors: list[str]) -> str:
    # Prefer one not used by another player in the room; fall back to a
    # deterministic choice if all are taken.
    for token in AVATAR_COLOR_TOKENS:
        if token not in existing_colors:
            return token
    # Deterministic fallback — reuse a palette colour.
    idx = sum(ord(c) for c in player_id) % len(AVATAR_COLOR_TOKENS)
    return AVATAR_COLOR_TOKENS[idx]
```

Wire it into the Player-creation path.

- [ ] **Step 6: Add the AVATAR_COLOR_TOKENS constant**

Create `backend/app/core/avatar.py`:

```python
"""Avatar colour tokens — must stay in sync with
frontend/src/composables/useAvatar.ts AVATAR_COLORS."""

AVATAR_COLOR_TOKENS: list[str] = [
    "avatar-1",
    "avatar-2",
    "avatar-3",
    "avatar-4",
    "avatar-5",
    "avatar-6",
]
```

- [ ] **Step 7: Write a backend test**

Create `backend/tests/unit/test_player_color.py`:

```python
from app.core.avatar import AVATAR_COLOR_TOKENS


def test_avatar_color_tokens_length() -> None:
    assert len(AVATAR_COLOR_TOKENS) == 6


def test_avatar_color_tokens_unique() -> None:
    assert len(set(AVATAR_COLOR_TOKENS)) == len(AVATAR_COLOR_TOKENS)
```

Add integration-style coverage — a test that creates two players in a room and asserts they get distinct colours from the palette. Drop into `backend/tests/integration/` if you prefer, or unit if your room manager has a light-weight path.

- [ ] **Step 8: Run backend tests + type-check**

```bash
uv run pytest tests/ -x -q
uv run ty check app/
```

Expected: all pass.

- [ ] **Step 9: Run the migration against the dev database to smoke-test it**

```bash
uv run alembic upgrade head
```

Expected: exit 0, new column present. Verify via `psql` or a quick Python shell if desired.

- [ ] **Step 10: Commit**

```bash
git add backend/app backend/alembic/versions backend/tests
git commit -m "feat(backend): add player color + default-assign on join"
```

## Task 8: backend — POST /api/rooms/quick-play endpoint

**Files:**

- Modify: `backend/app/rooms/router.py`
- Modify: `backend/app/rooms/schemas.py` — add `QuickPlayResponse`.
- Create: `backend/tests/unit/test_quick_play.py`.

Endpoint behaviour: return an existing public room that has `< MAX_PLAYERS` and is in the `lobby` phase, OR create a fresh public room and return it. Response shape mirrors `CreateRoomResponse` / `RandomRoomResponse` (just `room_code`).

- [ ] **Step 1: Add the response schema**

In `backend/app/rooms/schemas.py`:

```python
class QuickPlayResponse(BaseModel):
    room_code: str
    kind: Literal["existing", "created"]
```

`kind` is informational — clients don't need it but it aids debugging.

- [ ] **Step 2: Add the route**

In `backend/app/rooms/router.py`, add alongside the existing `@router.post("/")` handler:

```python
@router.post("/quick-play", response_model=QuickPlayResponse)
async def quick_play() -> QuickPlayResponse:
    room_code = await room_manager.find_joinable_public_room()
    if room_code is not None:
        return QuickPlayResponse(room_code=room_code, kind="existing")

    new_code = await room_manager.create_room()
    return QuickPlayResponse(room_code=new_code, kind="created")
```

- [ ] **Step 3: Implement the manager helper `find_joinable_public_room`**

In `backend/app/rooms/manager.py`, add:

```python
async def find_joinable_public_room(self) -> str | None:
    """Return a public room in lobby phase with < MAX_PLAYERS, or None."""
    for code, room in self._rooms.items():  # adapt to the actual accessor
        if room.is_public and room.phase == "lobby" and len(room.players) < MAX_PLAYERS:
            return code
    return None
```

Match the existing attribute/method names on the Room / RoomManager classes — the above is a guide, not verbatim.

- [ ] **Step 4: Write tests**

Create `backend/tests/unit/test_quick_play.py`:

```python
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_quick_play_creates_room_when_none_available() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/api/rooms/quick-play")
        assert r.status_code == 200
        body = r.json()
        assert "room_code" in body
        assert body["kind"] in {"existing", "created"}


@pytest.mark.asyncio
async def test_quick_play_returns_existing_room_when_one_has_space() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a public room in lobby first.
        create = await client.post("/api/rooms")
        assert create.status_code == 200
        expected = create.json()["room_code"]

        r = await client.post("/api/rooms/quick-play")
        assert r.status_code == 200
        body = r.json()
        # The newly-created empty public room should be the one returned.
        assert body["room_code"] == expected
        assert body["kind"] == "existing"
```

Adapt fixtures to match the project's existing pytest setup (e.g. use whatever app/session factory the other route tests use).

- [ ] **Step 5: Run tests**

```bash
cd backend
uv run pytest tests/ -x -q
uv run ty check app/
```

Expected: all pass.

- [ ] **Step 6: Regenerate the OpenAPI contract**

```bash
cd /Users/simon/code/personal/6-second-scribbles
just generate-contracts
# or: pnpm contracts:generate (from repo root)
```

Confirm `contracts/openapi.json` picks up `QuickPlayResponse` and `POST /rooms/quick-play`.

- [ ] **Step 7: Commit**

```bash
git add backend/app backend/tests contracts/openapi.json frontend/src/generated/api.ts
git commit -m "feat(backend): add POST /rooms/quick-play endpoint"
```

## Task 9: frontend — SettingsPanel composite + global gear button

**Files:**

- Create: `frontend/src/components/settings/SettingsPanel.vue`
- Create: `frontend/src/components/settings/__tests__/SettingsPanel.spec.ts`
- Modify: `frontend/src/App.vue` (mount the gear + panel globally)
- Modify: `frontend/src/i18n/en.json` + other locale files to add the new labels.

The composite owns the open state (`v-model:open` on a parent `HdSidepanel`), uses `useGameStore` + `useTheme` + `useSound` to read/write state, and renders:

1. Identity section — `HdAvatar` (lg) showing current color + initial, `HdInput` for name (debounced write), `AvatarColorPicker`.
2. Locale section — existing locale selector logic (can reuse `LocaleSelector.vue` for now; full re-skin can be a follow-up).
3. Theme section — `HdSegmented` with Light / Dark / Auto.
4. Sound section — `HdPill` status + `HdButton` toggle.
5. About section — links via `<i18n-t>` matching the existing footer text.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/settings/__tests__/SettingsPanel.spec.ts`:

```ts
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import { describe, expect, it } from "vitest";

import SettingsPanel from "@/components/settings/SettingsPanel.vue";

function mountPanel(initialState = {}) {
  return mount(SettingsPanel, {
    props: { open: true },
    global: {
      plugins: [createTestingPinia({ initialState: { game: initialState } })],
      stubs: { teleport: true },
    },
  });
}

describe("SettingsPanel", () => {
  it("shows the current player name in the name input", () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    expect((w.find('input[aria-label="Your name"]').element as HTMLInputElement).value).toBe("Simon");
  });

  it("renders a Light/Dark/Auto theme picker", () => {
    const w = mountPanel();
    const labels = w.findAll(".hd-seg__item").map((n) => n.text());
    expect(labels).toContain("Light");
    expect(labels).toContain("Dark");
    expect(labels).toContain("Auto");
  });

  it("renders a sound toggle", () => {
    const w = mountPanel();
    expect(w.text()).toMatch(/sound/i);
  });

  it("renders an avatar color picker with 6 swatches", () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    const picker = w.find('[role="radiogroup"][aria-label="Avatar color"]');
    expect(picker.exists()).toBe(true);
    expect(picker.findAll("button")).toHaveLength(6);
  });
});
```

Install `@pinia/testing` if not already present:

```bash
pnpm add -D @pinia/testing
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- SettingsPanel
```

Expected: FAIL.

- [ ] **Step 3: Implement the composite**

Create `frontend/src/components/settings/SettingsPanel.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import HdSegmented from "@/components/ui/HdSegmented.vue";
import HdSidepanel from "@/components/ui/HdSidepanel.vue";
import LocaleSelector from "@/components/LocaleSelector.vue";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { useSound } from "@/composables/useSound";
import { useTheme, type Theme } from "@/composables/useTheme";
import { useGameStore } from "@/stores/game";

const open = defineModel<boolean>("open", { default: false });

const store = useGameStore();
const { theme } = useTheme();
const { enabled: soundEnabled } = useSound();
const { localeOptions } = useLocaleAvailability();
const { t } = useI18n();

const playerName = computed({
  get: () => store.localPlayerName,
  set: (v: string) => {
    store.localPlayerName = v;
  },
});
const playerLocale = computed({
  get: () => store.localPlayerLocale,
  set: (v: string) => store.setLocalPlayerLocale(v),
});
const playerColor = computed({
  get: () => store.localPlayerColor,
  set: (v) => store.setLocalPlayerColor(v),
});
const initial = computed(() => getAvatarInitial(playerName.value || "?"));

const themeOptions: Array<{ value: Theme; label: string }> = [
  { value: "light", label: t("settings.themeLight") },
  { value: "dark", label: t("settings.themeDark") },
  { value: "auto", label: t("settings.themeAuto") },
];
</script>

<template>
  <HdSidepanel v-model:open="open" :title="t('settings.title')">
    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.identity") }}</h3>
      <div class="settings-identity">
        <HdAvatar :initial="initial" :color="playerColor" size="lg" />
        <HdInput v-model="playerName" :aria-label="t('settings.yourName')" :placeholder="t('settings.yourName')" />
      </div>
      <AvatarColorPicker v-model="playerColor" :initial="initial" />
    </section>

    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.language") }}</h3>
      <LocaleSelector v-model="playerLocale" :options="localeOptions" variant="pill" />
    </section>

    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.theme") }}</h3>
      <HdSegmented v-model="theme" :options="themeOptions" name="ds-theme" :aria-label="t('settings.theme')" />
    </section>

    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.sound") }}</h3>
      <div class="settings-sound">
        <HdPill :variant="soundEnabled ? 'success' : 'default'">
          {{ soundEnabled ? t("settings.soundOn") : t("settings.soundOff") }}
        </HdPill>
        <HdButton variant="secondary" @click="soundEnabled = !soundEnabled">
          {{ t("settings.toggle") }}
        </HdButton>
      </div>
    </section>

    <section class="settings-section settings-about">
      <h3 class="settings-section__title">{{ t("settings.about") }}</h3>
      <p class="settings-about__text">
        <i18n-t keypath="home.footerText" tag="span">
          <template #original>
            <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener">
              Six Second Scribbles
            </a>
          </template>
          <template #inspiration>
            <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener">
              Oliver Culley de Lange's solo version
            </a>
          </template>
          <template #source>
            <a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener">
              Source on GitHub
            </a>
          </template>
        </i18n-t>
      </p>
    </section>
  </HdSidepanel>
</template>

<style scoped>
.settings-section {
  padding: 16px 0;
  border-bottom: 1px dashed var(--color-ink);
}
.settings-section:last-child {
  border-bottom: 0;
}
.settings-section__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
  margin: 0 0 10px;
  color: var(--color-ink);
}
.settings-identity {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}
.settings-identity .hd-input {
  flex: 1;
}
.settings-sound {
  display: flex;
  gap: 12px;
  align-items: center;
}
.settings-about__text {
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
  line-height: 1.5;
}
.settings-about__text a {
  color: var(--color-ballpoint-blue);
  text-decoration: underline;
}
</style>
```

- [ ] **Step 4: Add i18n keys**

In `frontend/src/locales/en.json`, add under a `settings` namespace:

```json
{
  "settings": {
    "title": "Settings",
    "identity": "Identity",
    "yourName": "Your name",
    "language": "Language",
    "theme": "Theme",
    "themeLight": "Light",
    "themeDark": "Dark",
    "themeAuto": "Auto",
    "sound": "Sound",
    "soundOn": "on",
    "soundOff": "off",
    "toggle": "Toggle",
    "about": "About"
  }
}
```

Mirror the keys (with appropriately translated values or English placeholders) in the other locale files under `frontend/src/locales/`. English placeholders are acceptable for this sprint if you don't speak the target language — note it in `docs/superpowers/specs/` for later translation.

- [ ] **Step 5: Mount globally in App.vue**

Edit `frontend/src/App.vue` to add a top-right `HdIconButton` that toggles the panel, and render `SettingsPanel` once:

```vue
<script setup lang="ts">
// ... existing imports ...
import { ref } from "vue";

import HdIconButton from "@/components/ui/HdIconButton.vue";
import SettingsPanel from "@/components/settings/SettingsPanel.vue";

// ... existing composables + onMounted logic ...

const settingsOpen = ref(false);
</script>

<template>
  <div id="app">
    <HdIconButton
      class="app-settings-btn"
      :label="$t('settings.title')"
      @click="settingsOpen = true"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    </HdIconButton>

    <RouterView />
    <ToastContainer />
    <SettingsPanel v-model:open="settingsOpen" />
  </div>
</template>

<style scoped>
.app-settings-btn {
  position: fixed;
  top: max(12px, env(safe-area-inset-top));
  right: max(12px, env(safe-area-inset-right));
  z-index: 50;
}
</style>
```

Leave the existing `ToastContainer` in place for now — Task 12 migrates it.

- [ ] **Step 6: Run tests + type-check**

```bash
pnpm test:unit -- SettingsPanel
pnpm type-check
```

Expected: the 4 SettingsPanel tests pass; full suite still green.

- [ ] **Step 7: Visual smoke test**

```bash
pnpm dev
```

Open the running dev URL; the gear icon appears top-right. Click it → panel slides in. Tab to each section. Close via X / backdrop / Escape. Kill the server.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.vue frontend/src/components/settings frontend/src/locales
git commit -m "feat(frontend): add global SettingsPanel with gear button"
```

## Task 10: frontend — HomeCreateJoin + HowToPlayDialog + Home rebuild

**Files:**

- Create: `frontend/src/components/home/HomeCreateJoin.vue`
- Create: `frontend/src/components/home/HowToPlayDialog.vue`
- Create/rewrite: `frontend/src/components/home/__tests__/HomeCreateJoin.spec.ts`
- Modify: `frontend/src/views/HomeView.vue` (full rewrite)
- Modify: `frontend/src/views/__tests__/HomeView.spec.ts` if present (rewrite; look for existing coverage patterns).

`HomeCreateJoin` owns: Start-a-room button, Find-random button, room-code input + Join button, Quick-play post-it strip. All styled with `Hd*` primitives. Uses the same `apiRequest` + generated schemas as the current `CreateJoinCard.vue` — keep the logic, change the presentation.

- [ ] **Step 1: Rewrite the test first**

Create `frontend/src/components/home/__tests__/HomeCreateJoin.spec.ts` (covers the behavioural assertions, not the CSS). Mirror the existing `CreateJoinCard.spec.ts` structure for mocks (router, api, notifications, connection). Verify:

- Renders the three CTAs (Start, Find random, Quick-play) and the code input with Join button.
- Clicking "Start a room" prompts for name when empty (opens `SettingsPanel`? or inline dialog? Simplest for this sprint: if name empty, open the settings panel and do not proceed — test that behaviour).
- Clicking Quick-play calls `POST /api/rooms/quick-play` and navigates.
- Clicking Join with a valid code calls the status endpoint then navigates.
- Clicking Join with an invalid code surfaces a toast via `showNotification`.

The test file will be lengthy — base it on `frontend/src/components/__tests__/CreateJoinCard.spec.ts` for the mocking scaffolding and extend with the new assertions.

- [ ] **Step 2: Run test to verify it fails**

```bash
pnpm test:unit -- HomeCreateJoin
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement `HomeCreateJoin.vue`**

Compose `HdCard`, `HdButton` (primary/secondary/success), `HdInput` (code variant). Mirror the existing `CreateJoinCard.vue` API (`createRoom`, `joinRoom`, `joinRandomRoom`), add a new `quickPlay()` handler calling `/api/rooms/quick-play`. Guard `createRoom` / `joinRoom` / `joinRandomRoom` / `quickPlay` with "name must be set" — if `store.localPlayerName.trim()` is empty, emit an `open-settings` event (parent uses it to open the global panel). Full code mirrors the structure of the old `CreateJoinCard.vue` so the test scaffolding transfers cleanly.

Keep this task's code block focused — the component template is roughly:

```vue
<template>
  <HdCard class="home-cta">
    <div class="home-cta__primary">
      <HdButton variant="primary" @click="handleCreateRoom">{{ t("home.createRoom") }}</HdButton>
      <HdButton variant="secondary" :disabled="isJoiningRandom" @click="handleJoinRandomRoom">
        {{ t("home.joinRandomRoom") }}
      </HdButton>
    </div>

    <div class="home-cta__join">
      <HdInput v-model="roomCodeModel" variant="code" :aria-label="t('home.roomCodeLabel')" />
      <HdButton variant="success" :disabled="isCheckingRoom" @click="handleJoinRoom">
        {{ t("home.joinRoom") }}
      </HdButton>
    </div>

    <HdCard variant="postit" class="home-cta__quick">
      <div>
        <strong>{{ t("home.quickPlayHeading") }}</strong>
        <p>{{ t("home.quickPlayBody") }}</p>
      </div>
      <HdButton variant="secondary" :disabled="isQuickPlaying" @click="handleQuickPlay">
        {{ t("home.quickPlayCta") }}
      </HdButton>
    </HdCard>
  </HdCard>
</template>
```

Script logic: copy + adapt from `CreateJoinCard.vue`, swapping `NamePromptDialog` calls for `emit('open-settings')`. Call `apiRequest('/api/rooms/quick-play', { method: 'POST', schema: QuickPlayResponseSchema })` for Quick-play (Zod schema must exist post-Task-8 regeneration).

- [ ] **Step 4: Implement `HowToPlayDialog.vue`**

A thin wrapper around `HdDialog` that renders the four-step how-to-play list from `home.step1..step4`. No confirm/cancel distinction — single OK button.

- [ ] **Step 5: Rewrite `HomeView.vue`**

Replace the current template with:

```vue
<template>
  <div class="home-page">
    <header class="home-hero">
      <h1 class="home-wordmark">{{ t("home.title") }}</h1>
      <p class="home-tagline">{{ t("home.tagline") }}</p>
    </header>

    <main class="home-main">
      <HomeCreateJoin @open-settings="settingsOpen = true" />
    </main>

    <footer class="home-footer">
      <button type="button" class="home-footer__how" @click="howOpen = true">
        {{ t("home.howToPlay") }}
      </button>
    </footer>

    <HowToPlayDialog v-model:open="howOpen" />
  </div>
</template>
```

Script section: small `const howOpen = ref(false)`; `SettingsPanel` is already mounted in `App.vue` (Task 9), so Home just emits the event the parent listens to. If the parent-child wiring is cleaner via a Pinia action `openSettings()` that `App.vue` reacts to, prefer that — the explicit event is given only as a fallback.

Add the `tagline` i18n key (`"Doodle. Guess. Laugh."`) alongside the existing `home.title`.

Delete `frontend/src/views/HomeView.vue`'s old imports of `HomePlayerPreferences` and `HowToPlay`.

- [ ] **Step 6: Run tests + type-check**

```bash
pnpm test:unit
pnpm type-check
```

Expected: all pass. Old `HomePlayerPreferences`-related tests (if any) must be deleted or updated. New `HomeCreateJoin` tests pass.

- [ ] **Step 7: Visual smoke**

```bash
pnpm dev
```

Open `http://localhost:<port>/`. Expect: wordmark on cream, single card with three CTAs + code input + yellow quick-play strip. Gear icon top-right opens the panel. Kill the server.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/HomeView.vue \
        frontend/src/components/home frontend/src/locales
git commit -m "feat(frontend): rebuild Home screen on Hd primitives + quick-play"
```

## Task 11: frontend — Lobby rebuild

**Files:**

- Create: `frontend/src/components/lobby/LobbyTopbar.vue`
- Create: `frontend/src/components/lobby/LobbyPlayerList.vue`
- Create: `frontend/src/components/lobby/LobbyGameSettings.vue`
- Create: `frontend/src/components/lobby/__tests__/*.spec.ts` for each
- Modify: `frontend/src/views/LobbyView.vue` (full rewrite using the above)
- Modify: `frontend/src/views/__tests__/LobbyView.spec.ts` if present

Behavioural parity with the current Lobby — read & modify `useGameStore` in the same way the current `LobbyView.vue`, `PlayerListPanel.vue`, and `GameSettingsPanel.vue` do; rebuild the templates against `Hd*` primitives.

- [ ] **Step 1: Inventory the current lobby surface**

```bash
sed -n '1,60p' frontend/src/views/LobbyView.vue
sed -n '1,80p' frontend/src/components/PlayerListPanel.vue
sed -n '1,80p' frontend/src/components/GameSettingsPanel.vue
```

List the events / store actions each currently calls. Record them inline in your working notes so the rewrite hits the same behaviour.

- [ ] **Step 2: Build `LobbyTopbar.vue`**

Layout: `HdButton` (secondary) leave + yellow-highlighter `HdPill` or `HdCard`-postit room code chip (with copy button via `useClipboard`). Spec for copy-to-clipboard feedback: use the existing `showNotification("Copied!")` pattern.

Test for `LobbyTopbar`: renders leave button, renders room code, emits `leave` on leave click, calls clipboard + showNotification on copy.

- [ ] **Step 3: Build `LobbyPlayerList.vue`**

Renders one row per `store.playersList` entry: `HdAvatar` (using `player.color` from server if present, else `getAvatarColor(player.id)`) + name + role badge (host vs player) + ready state. Tests: one row per player, avatar colour passed through, "you" row highlighted.

- [ ] **Step 4: Build `LobbyGameSettings.vue`**

Inline collapsible (expand/collapse via `HdIconButton` chevron) with difficulty radios (`HdSegmented`), rounds stepper (reuse existing `StepperInput.vue` if it fits), drawing-time stepper, guessing-time stepper. Read/write via `useGameStore`. Only the host sees interactive controls — others see read-only values.

- [ ] **Step 5: Rewrite `LobbyView.vue`**

Composition:

```vue
<template>
  <div class="lobby-page">
    <LobbyTopbar :room-code="roomCode" @leave="showLeaveDialog" />

    <div class="lobby-grid">
      <HdCard class="lobby-main">
        <LobbyPlayerList />
        <LobbyGameSettings />
        <HdButton
          v-if="store.isHost"
          variant="primary"
          :disabled="!canStart"
          class="lobby-start"
          @click="startGame"
        >
          {{ canStart ? t("lobby.startGame") : t("lobby.waitingForPlayers") }}
        </HdButton>
        <HdCard v-else variant="postit" class="lobby-waiting">
          {{ playerCount >= 2 ? t("lobby.waitingForHost") : t("lobby.waitingForMore") }}
        </HdCard>
      </HdCard>

      <div v-if="store.isHost || store.roomPadVisible" class="lobby-drawpad">
        <!-- Existing SharedDrawpad, wrapped in HdCard, re-skinned tool row -->
      </div>
    </div>

    <HdDialog
      v-model:open="leaveDialogOpen"
      :title="leaveDialog.title"
      :message="leaveDialog.message"
      :confirm-label="leaveDialog.confirmLabel"
      :cancel-label="leaveDialog.cancelLabel"
      variant="danger"
      @confirm="confirmLeave"
    />
  </div>
</template>
```

Script section copy-ports the current `LobbyView.vue`'s logic (`useGameConnection`, `useRoomLeave`, `canStart`, `startGame`, etc.).

- [ ] **Step 6: Run tests + type-check**

```bash
pnpm test:unit
pnpm type-check
```

Expected: all pass. Any existing `LobbyView.spec.ts` / `PlayerListPanel.spec.ts` must be updated for the new DOM structure.

- [ ] **Step 7: Visual smoke**

```bash
pnpm dev
```

Create a room, verify: topbar with yellow code chip, player list with avatar colours, settings expand/collapse, Start button disabled until ≥2 players. Host-only vs. non-host UI renders correctly. Kill the server.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/LobbyView.vue frontend/src/components/lobby frontend/src/locales
git commit -m "feat(frontend): rebuild Lobby screen on Hd primitives with avatars + room-code chip"
```

## Task 12: frontend — migrate ToastContainer & ConfirmDialog callers, delete legacy

**Files:**

- Modify: every file that currently imports `ToastContainer` or `ConfirmDialog` — replace with `HdToast` / `HdDialog`.
- Delete: `frontend/src/components/ToastContainer.vue`, `frontend/src/components/ConfirmDialog.vue`.
- Delete: `frontend/src/components/CreateJoinCard.vue`, `HomePlayerPreferences.vue`, `HowToPlay.vue`, `NamePromptDialog.vue`, `RoomCodeInput.vue`, `PlayerListPanel.vue`, `GameSettingsPanel.vue` — only after confirming no imports remain.
- Delete: `frontend/src/components/__tests__/*.spec.ts` for the above components (the new components in `home/`, `lobby/`, `settings/` have their own specs already).

- [ ] **Step 1: Find callers**

```bash
grep -rn "from \"@/components/ToastContainer\|from \"@/components/ConfirmDialog\|from \"@/components/CreateJoinCard\|from \"@/components/HomePlayerPreferences\|from \"@/components/HowToPlay\|from \"@/components/NamePromptDialog\|from \"@/components/RoomCodeInput\|from \"@/components/PlayerListPanel\|from \"@/components/GameSettingsPanel" frontend/src
```

For each match, edit the importing file to use the new component instead. Likely callers: `App.vue` (ToastContainer), various views (ConfirmDialog).

- [ ] **Step 2: Run tests + build**

```bash
pnpm test:unit
pnpm type-check
pnpm build
```

Expected: all pass — any residual imports of deleted files would surface here.

- [ ] **Step 3: Delete the legacy files**

```bash
git rm frontend/src/components/ToastContainer.vue \
       frontend/src/components/ConfirmDialog.vue \
       frontend/src/components/CreateJoinCard.vue \
       frontend/src/components/HomePlayerPreferences.vue \
       frontend/src/components/HowToPlay.vue \
       frontend/src/components/NamePromptDialog.vue \
       frontend/src/components/RoomCodeInput.vue \
       frontend/src/components/PlayerListPanel.vue \
       frontend/src/components/GameSettingsPanel.vue \
       frontend/src/components/__tests__/CreateJoinCard.spec.ts \
       frontend/src/components/__tests__/LocaleSelector.spec.ts \
       frontend/src/components/__tests__/PlayerListPanel.spec.ts \
       frontend/src/components/__tests__/RoomCodeInput.spec.ts
```

Keep `LocaleSelector.vue` — still used by `SettingsPanel`. Only delete the specs of components you actually deleted; verify each `git rm` target exists first via `ls`.

- [ ] **Step 4: Run tests + build again**

```bash
pnpm test:unit
pnpm type-check
pnpm lint
pnpm build
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore(frontend): migrate to Hd primitives, delete legacy components"
```

## Task 13: Full Sprint 1 check suite + visual QA

- [ ] **Step 1: Run the whole battery**

```bash
cd /Users/simon/code/personal/6-second-scribbles/.worktrees/redesign-sprint-0/frontend
pnpm test:unit
pnpm type-check
pnpm lint
pnpm build
cd ../backend
uv run pytest tests/ -x -q
uv run ty check app/
```

Expected: every command exits 0.

- [ ] **Step 2: Dev-server end-to-end smoke**

Start both servers (`just dev` from repo root), then in a browser:

1. Load `/` — confirm Home renders in the new aesthetic, gear icon top-right, quick-play strip visible.
2. Open Settings — identity / language / theme / sound / about sections present. Change name, locale, avatar colour, theme — all persist across reload.
3. Click "Start a room" — taken to `/rooms/<code>`; Lobby renders with new topbar, player list shows your avatar.
4. Click Quick-play from Home — creates/joins a public room.
5. Toggle dark mode from Settings — Home and Lobby both flip correctly; yellow post-its and success buttons remain readable.
6. Open the How-to-play dialog from the footer — renders the four steps.

- [ ] **Step 3: Accessibility pass**

On both Home and Lobby:

- Tab through — focus rings on every interactive control, logical order.
- Press the gear icon with keyboard — settings open, focus moves into the panel.
- Press Escape — panel closes.
- Screen-reader spot-check: avatar has `aria-hidden`, theme segmented uses real radios, settings sections have `h3` headings.

- [ ] **Step 4: Regenerate contracts if anything drifted**

```bash
cd /Users/simon/code/personal/6-second-scribbles
just generate-contracts
git diff contracts/ frontend/src/generated/
```

If the diff is empty, nothing to commit.

- [ ] **Step 5: Commit any drift + write a sprint-summary commit**

```bash
# If contracts/ drifted:
git add contracts/ frontend/src/generated/
git commit -m "chore(contracts): regenerate after Sprint 1"
```

## Sprint 1 acceptance check

Re-read §10 of the spec. For each criterion:

1. ✅ Tokens-only UI — verify new files via `grep -rn "#[0-9a-fA-F]\{3,\}" frontend/src/components/{home,lobby,settings,ui}/*.vue` (should only find paper-texture noise SVG url references, no hex).
2. ✅ Light + dark WCAG AA — run Lighthouse on the new Home + Lobby in both modes.
3. ✅ Visible focus, keyboard reachable — manually Tab through Home + Lobby + SettingsPanel.
4. ✅ Reduced motion respected — `prefers-reduced-motion: reduce` still no-ops transforms.
5. ✅ 375 / 768 / 1024 / 1440 widths — spot-check each layout at each width.
6. ✅ No emoji in structural UI — grep: `grep -rn "[\x{1F300}-\x{1FAFF}]" frontend/src/components/{home,lobby,settings}` should return nothing.
7. ✅ New features E2E — quick-play, avatar colour, settings panel, theme persistence all verified in Step 2.
8. ✅ Existing suites pass — verified in Step 1.

## Hand-off to Sprint 2

Sprint 2 (Drawing + Guessing) will:

- Rewrite `DrawingPhase.vue` and `GuessingPhase.vue` using `Hd*` primitives, the new dark ink-bar header with sound toggle + `HdTimer`, dot-grid canvas.
- Wire ambient sound cues (round-start chime, last-10s tick, reveal stinger, click) using `useSound`.
- Drop any old scoped styles that still reference pre-redesign tokens.

The Sprint 2 plan is written separately at `docs/superpowers/plans/<date>-ui-redesign-sprint-2-drawing-guessing.md` when ready to execute.
