<script lang="ts">
import { tick, untrack } from "svelte";
import { fly } from "svelte/transition";
import AvatarColorPicker from "@/components/settings/AvatarColorPicker.svelte";
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdDialog from "@/components/ui/HdDialog.svelte";
import HdInput from "@/components/ui/HdInput.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useSettingsPanel } from "@/composables/useSettingsPanel.svelte";
import { useSound } from "@/composables/useSound.svelte";
import { type Theme, useTheme } from "@/composables/useTheme.svelte";
import { t } from "@/i18n";
import { formatLocaleLabel, SUPPORTED_LOCALES } from "@/shared/locales";
import { useGameStore } from "@/stores/game.svelte";

let { open = $bindable(false) }: { open?: boolean } = $props();

const store = useGameStore();
const themeState = useTheme();
const sound = useSound();
const settingsPanel = useSettingsPanel();
let nameInputRef = $state<ReturnType<typeof HdInput> | null>(null);

let watchStarted0 = false;
$effect(() => {
  const value = settingsPanel.focusNameOnOpen;
  if (!watchStarted0) {
    watchStarted0 = true;
    return;
  }
  untrack(() => {
    const v = value;
    if (v) {
      tick().then(() => {
        nameInputRef?.focus();
        settingsPanel.focusNameOnOpen = false;
      });
    }
  });
});

// Resume the action that opened the panel for a name (e.g. Create Room),
// now that the player has picked one — so they don't have to click twice.
// HdDialog closes itself on Escape, the backdrop and its close button, then emits cancel.
function resumePendingAction() {
  const action = settingsPanel.pendingNameAction;
  settingsPanel.pendingNameAction = null;
  if (action && store.localPlayerName.trim()) action();
}

function close() {
  open = false;
  resumePendingAction();
}

let initial = $derived.by(() => getAvatarInitial(store.localPlayerName || "?"));

// Avatar color picker
let colorPickerOpen = $state(false);

// Locale picker — rendered as a top-layer popover so it can't be clipped
// by the dialog's overflow. Position is anchored to the trigger on open.
let localeBtnRef = $state<HTMLButtonElement | null>(null);
let localePopoverRef = $state<HTMLDivElement | null>(null);
let localeOpen = $state(false);

function onLocaleToggle(e: Event) {
  const opened = (e as { newState?: string }).newState === "open";
  localeOpen = opened;
  const btn = localeBtnRef;
  const pop = localePopoverRef;
  if (!opened || !btn || !pop) return;
  const r = btn.getBoundingClientRect();
  pop.style.top = `${r.bottom + 6}px`;
  pop.style.right = `${window.innerWidth - r.right}px`;
  pop.style.left = "auto";
}
function selectLocale(code: string) {
  store.setLocalPlayerLocale(code);
  localePopoverRef?.hidePopover();
}

// Theme — light / dark / auto segmented toggle
let themeOptions = $derived.by<Array<{ value: Theme; label: string }>>(() => [
  { value: "light", label: t("settings.themeLight") },
  { value: "dark", label: t("settings.themeDark") },
  { value: "auto", label: t("settings.themeAuto") },
]);
function selectTheme(value: Theme) {
  themeState.theme = value;
}
</script>

<HdDialog
  class="settings-dialog"
  bind:open
  title={t("settings.title")}
  closeLabel={t("common.close")}
  actions={false}
  oncancel={resumePendingAction}
>
  <div class="settings-dialog__body">
    <!-- Identity -->
    <section class="settings-section">
      <h3 class="settings-section__title">{t("settings.identity")}</h3>
      {#if settingsPanel.pendingNameAction}
        <p class="settings-hint">{t("settings.namePrompt")}</p>
      {/if}
      <div class="settings-identity">
        <button
          class="avatar-btn"
          type="button"
          aria-label={t("common.color")}
          aria-expanded={colorPickerOpen}
          onclick={() => {
            colorPickerOpen = !colorPickerOpen;
          }}
        >
          <HdAvatar {initial} color={store.localAvatarColor} size="lg"></HdAvatar>
          <span class="avatar-btn__edit" aria-hidden="true">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
            </svg>
          </span>
        </button>
        <HdInput
          bind:this={nameInputRef}
          bind:modelValue={store.localPlayerName}
          ariaLabel={t("settings.yourName")}
          placeholder={t("settings.namePlaceholder")}
          onkeyup={(event) => {
            if (event.key === "Enter") close();
          }}
        ></HdInput>
      </div>

      {#if colorPickerOpen}
        <div
          class="avatar-colors"
          transition:fly={{ y: -6, duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 220 }}
        >
          <AvatarColorPicker
            modelValue={store.localAvatarColor}
            onmodelValueChange={store.setLocalPlayerColor}
            {initial}
          ></AvatarColorPicker>
        </div>
      {/if}
    </section>

    <!-- Preferences: language · appearance · sound -->
    <section class="settings-section settings-prefs">
      <!-- Language -->
      <div class="pref-row">
        <span class="pref-row__label">
          <svg
            class="pref-row__icon"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
          {t("settings.language")}
        </span>
        <button
          class="locale-trigger"
          bind:this={localeBtnRef}
          type="button"
          aria-label={`${t("settings.language")}: ${formatLocaleLabel(store.localPlayerLocale)}`}
          aria-expanded={localeOpen}
          popovertarget="settings-locale-popover"
        >
          <span class="locale-trigger__text">{formatLocaleLabel(store.localPlayerLocale)}</span>
          <svg
            class={["locale-trigger__chevron", { "locale-trigger__chevron--open": localeOpen }]}
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <div
          class="locale-popover"
          id="settings-locale-popover"
          bind:this={localePopoverRef}
          popover
          role="listbox"
          aria-label={t("settings.language")}
          ontoggle={onLocaleToggle}
        >
          {#each SUPPORTED_LOCALES as code (code)}
            <button
              class={["locale-popover__option", { "locale-popover__option--active": store.localPlayerLocale === code }]}
              type="button"
              role="option"
              aria-selected={store.localPlayerLocale === code}
              onclick={() => {
                selectLocale(code);
              }}
            >
              {formatLocaleLabel(code)}
            </button>
          {/each}
        </div>
      </div>

      <!-- Appearance -->
      <div class="pref-row">
        <span class="pref-row__label">
          <svg
            class="pref-row__icon"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="9"></circle>
            <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none"></path>
          </svg>
          {t("settings.theme")}
        </span>
        <div class="seg" role="radiogroup" aria-label={t("settings.theme")}>
          {#each themeOptions as opt (opt.value)}
            <label class={["seg__btn", { "seg__btn--active": themeState.theme === opt.value }]} title={opt.label}>
              <input
                class="seg__input"
                type="radio"
                name="settings-theme"
                value={opt.value}
                checked={themeState.theme === opt.value}
                aria-label={opt.label}
                onchange={() => {
                  selectTheme(opt.value);
                }}
              >
              <!-- Sun (light) -->
              {#if opt.value === "light"}
                <svg
                  class="seg__icon"
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <circle cx="12" cy="12" r="4"></circle>
                  <line x1="12" y1="2" x2="12" y2="6"></line>
                  <line x1="12" y1="18" x2="12" y2="22"></line>
                  <line x1="4.22" y1="4.22" x2="7.05" y2="7.05"></line>
                  <line x1="16.95" y1="16.95" x2="19.78" y2="19.78"></line>
                  <line x1="2" y1="12" x2="6" y2="12"></line>
                  <line x1="18" y1="12" x2="22" y2="12"></line>
                  <line x1="4.22" y1="19.78" x2="7.05" y2="16.95"></line>
                  <line x1="16.95" y1="7.05" x2="19.78" y2="4.22"></line>
                </svg>
                <!-- Moon (dark) -->
              {:else if opt.value === "dark"}
                <svg
                  class="seg__icon"
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                </svg>
                <!-- Monitor (auto) -->
              {:else}
                <svg
                  class="seg__icon"
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                  <line x1="8" y1="21" x2="16" y2="21"></line>
                  <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
              {/if}</label
            >
          {/each}
        </div>
      </div>

      <!-- Sound -->
      <div class="pref-row">
        <span class="pref-row__label">
          <svg
            class="pref-row__icon"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
          </svg>
          {t("settings.sound")}
        </span>
        <label class={["switch", { "switch--on": sound.enabled }]}>
          <input
            class="switch__input"
            type="checkbox"
            checked={sound.enabled}
            aria-label={sound.enabled ? t("settings.soundOn") : t("settings.soundOff")}
            onchange={() => {
              sound.enabled = !sound.enabled;
            }}
          >
          <span class="switch__thumb" aria-hidden="true"></span>
        </label>
      </div>
    </section>
  </div>
</HdDialog>

<style>
/* ─── Dialog shell (HdDialog, laid out as a fixed header over a scrolling body) ─── */
:global(dialog.hd-dialog.settings-dialog) {
  max-height: min(640px, calc(100vh - 48px));
  padding: 0;
  overflow: hidden;
}
:global(dialog.hd-dialog.settings-dialog[open]) {
  display: flex;
  flex-direction: column;
}
:global(dialog.hd-dialog.settings-dialog) :global(.hd-dialog__header) {
  margin: 0;
  padding: 16px 20px;
  border-bottom: 1.5px dashed var(--color-ink);
  flex-shrink: 0;
}
.settings-dialog__body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

/* ─── Sections ─── */
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

/* ─── Identity ─── */
.settings-hint {
  margin: 0 0 12px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
}
.settings-identity {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 4px;
}

.avatar-btn {
  position: relative;
  background: transparent;
  border: 0;
  padding: 0;
  cursor: pointer;
  flex-shrink: 0;
}
.avatar-btn__edit {
  position: absolute;
  bottom: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  background: var(--color-card);
  border: 1.5px solid var(--color-ink);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 1px 1px 0 var(--color-ink);
}
.avatar-btn__edit svg {
  width: 10px;
  height: 10px;
  stroke: var(--color-ink);
}

.avatar-colors {
  padding-top: 12px;
}
/* ─── Preferences (language · appearance · sound) ─── */
.settings-prefs {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pref-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
}
.pref-row__label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
}
.pref-row__icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Language trigger + top-layer popover (escapes dialog clipping) */
.locale-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 55%;
  min-height: 44px;
  padding: 6px 12px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
}
.locale-trigger__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.locale-trigger__chevron {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.6;
  transition: transform var(--motion-fast) var(--ease-out);
}
.locale-trigger__chevron--open {
  transform: rotate(180deg);
}

.locale-popover {
  position: fixed;
  margin: 0;
  inset: auto;
  min-width: 180px;
  max-height: 260px;
  overflow-y: auto;
  padding: 4px;
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
}
.locale-popover__option {
  display: block;
  width: 100%;
  padding: 10px 12px;
  background: transparent;
  border: 0;
  border-radius: calc(var(--r-card) - 6px);
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  text-align: left;
  cursor: pointer;
}
.locale-popover__option:hover {
  background: color-mix(in srgb, var(--color-ink) 8%, transparent);
}
.locale-popover__option--active {
  font-weight: 700;
  background: color-mix(in srgb, var(--color-ink) 12%, transparent);
}

/* Appearance segmented control */
.seg {
  display: inline-flex;
  flex-shrink: 0;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  overflow: hidden;
}
.seg__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  min-height: 40px;
  color: var(--color-ink);
  cursor: pointer;
}
.seg__btn + .seg__btn {
  border-left: 1.5px solid var(--color-ink);
}
.seg__input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.seg__btn--active {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.seg__btn:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: -3px;
}
.seg__icon {
  width: 18px;
  height: 18px;
}

/* Sound switch */
.switch {
  position: relative;
  width: 52px;
  height: 30px;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--color-ink) 20%, transparent);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-out);
}
.switch--on {
  background: var(--color-highlighter-yellow);
}
.switch__input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.switch__thumb {
  position: absolute;
  top: 50%;
  left: 2px;
  width: 22px;
  height: 22px;
  transform: translateY(-50%);
  background: var(--color-card);
  border: 1.5px solid var(--color-ink);
  border-radius: 50%;
  transition: left var(--motion-fast) var(--ease-out);
}
.switch--on .switch__thumb {
  left: 24px;
}
.switch:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
