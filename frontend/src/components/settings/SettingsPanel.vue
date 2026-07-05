<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from "vue";
import { useI18n } from "vue-i18n";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";
import HdInput from "@/components/ui/HdInput.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useSettingsPanel } from "@/composables/useSettingsPanel";
import { useSound } from "@/composables/useSound";
import { type Theme, useTheme } from "@/composables/useTheme";
import { formatLocaleLabel, SUPPORTED_LOCALES } from "@/shared/locales";
import { useGameStore } from "@/stores/game";

const open = defineModel<boolean>("open", { default: false });

const store = useGameStore();
const { theme } = useTheme();
const { enabled: soundEnabled } = useSound();
const { focusNameOnOpen, pendingNameAction } = useSettingsPanel();
const nameInputRef = useTemplateRef<InstanceType<typeof HdInput>>("nameInput");
const dialogRef = useTemplateRef<HTMLDialogElement>("dialog");

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

watch(focusNameOnOpen, (v) => {
  if (v) {
    nextTick(() => {
      nameInputRef.value?.focus();
      focusNameOnOpen.value = false;
    });
  }
});

const { t } = useI18n({ useScope: "global" });

function close() {
  open.value = false;
  // Resume the action that opened the panel for a name (e.g. Create Room),
  // now that the player has picked one — so they don't have to click twice.
  const action = pendingNameAction.value;
  pendingNameAction.value = null;
  if (action && store.localPlayerName.trim()) action();
}

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
  get: () => store.localPlayerColor ?? getAvatarColor(store.localPlayerId),
  set: (v) => store.setLocalPlayerColor(v),
});
const initial = computed(() => getAvatarInitial(playerName.value || "?"));

// Avatar color picker
const colorPickerOpen = ref(false);

// Locale picker — rendered as a top-layer popover so it can't be clipped
// by the dialog's overflow. Position is anchored to the trigger on open.
const localeBtnRef = ref<HTMLButtonElement | null>(null);
const localePopoverRef = ref<HTMLDivElement | null>(null);
const localeOpen = ref(false);

function onLocaleToggle(e: Event) {
  const opened = (e as { newState?: string }).newState === "open";
  localeOpen.value = opened;
  const btn = localeBtnRef.value;
  const pop = localePopoverRef.value;
  if (!opened || !btn || !pop) return;
  const r = btn.getBoundingClientRect();
  pop.style.top = `${r.bottom + 6}px`;
  pop.style.right = `${window.innerWidth - r.right}px`;
  pop.style.left = "auto";
}
function selectLocale(code: string) {
  playerLocale.value = code;
  localePopoverRef.value?.hidePopover();
}

// Theme — light / dark / auto segmented toggle
const themeOptions = computed<Array<{ value: Theme; label: string }>>(() => [
  { value: "light", label: t("settings.themeLight") },
  { value: "dark", label: t("settings.themeDark") },
  { value: "auto", label: t("settings.themeAuto") },
]);
function selectTheme(value: Theme) {
  theme.value = value;
}
</script>

<template>
  <dialog ref="dialog" class="settings-dialog" @click.self="close" @close="close">
    <header class="settings-dialog__header">
      <h2 class="settings-dialog__title">{{ t("settings.title") }}</h2>
      <HdIconButton label="Close" variant="ghost" data-testid="settings-close" @click="close">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </HdIconButton>
    </header>

    <div class="settings-dialog__body">
      <!-- Identity -->
      <section class="settings-section">
        <h3 class="settings-section__title">{{ t("settings.identity") }}</h3>
        <p v-if="pendingNameAction" class="settings-hint">{{ t("settings.namePrompt") }}</p>
        <div class="settings-identity">
          <button
            type="button"
            class="avatar-btn"
            :aria-label="t('common.color')"
            :aria-expanded="colorPickerOpen"
            @click="colorPickerOpen = !colorPickerOpen"
          >
            <HdAvatar :initial="initial" :color="playerColor" size="lg" />
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
                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
              </svg>
            </span>
          </button>
          <HdInput
            ref="nameInput"
            v-model="playerName"
            :aria-label="t('settings.yourName')"
            :placeholder="t('settings.namePlaceholder')"
            @keyup.enter="close"
          />
        </div>
        <Transition name="settings-expand">
          <div v-if="colorPickerOpen" class="avatar-colors">
            <AvatarColorPicker v-model="playerColor" :initial="initial" />
          </div>
        </Transition>
      </section>

      <!-- Preferences: language · appearance · sound -->
      <section class="settings-section settings-prefs">
        <!-- Language -->
        <div class="pref-row">
          <span class="pref-row__label">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="pref-row__icon"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            {{ t("settings.language") }}
          </span>
          <button
            ref="localeBtnRef"
            type="button"
            class="locale-trigger"
            :aria-label="t('settings.language')"
            :aria-expanded="localeOpen"
            popovertarget="settings-locale-popover"
          >
            <span class="locale-trigger__text">{{ formatLocaleLabel(playerLocale) }}</span>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="locale-trigger__chevron"
              :class="{ 'locale-trigger__chevron--open': localeOpen }"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div
            id="settings-locale-popover"
            ref="localePopoverRef"
            popover
            class="locale-popover"
            role="listbox"
            :aria-label="t('settings.language')"
            @toggle="onLocaleToggle"
          >
            <button
              v-for="code in SUPPORTED_LOCALES"
              :key="code"
              type="button"
              role="option"
              class="locale-popover__option"
              :class="{ 'locale-popover__option--active': playerLocale === code }"
              :aria-selected="playerLocale === code"
              @click="selectLocale(code)"
            >
              {{ formatLocaleLabel(code) }}
            </button>
          </div>
        </div>

        <!-- Appearance -->
        <div class="pref-row">
          <span class="pref-row__label">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="pref-row__icon"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none" />
            </svg>
            {{ t("settings.theme") }}
          </span>
          <div class="seg" role="radiogroup" :aria-label="t('settings.theme')">
            <label
              v-for="opt in themeOptions"
              :key="opt.value"
              class="seg__btn"
              :class="{ 'seg__btn--active': theme === opt.value }"
              :title="opt.label"
            >
              <input
                type="radio"
                class="seg__input"
                name="settings-theme"
                :value="opt.value"
                :checked="theme === opt.value"
                :aria-label="opt.label"
                @change="selectTheme(opt.value)"
              >
              <!-- Sun (light) -->
              <svg
                v-if="opt.value === 'light'"
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="seg__icon"
              >
                <circle cx="12" cy="12" r="4" />
                <line x1="12" y1="2" x2="12" y2="6" />
                <line x1="12" y1="18" x2="12" y2="22" />
                <line x1="4.22" y1="4.22" x2="7.05" y2="7.05" />
                <line x1="16.95" y1="16.95" x2="19.78" y2="19.78" />
                <line x1="2" y1="12" x2="6" y2="12" />
                <line x1="18" y1="12" x2="22" y2="12" />
                <line x1="4.22" y1="19.78" x2="7.05" y2="16.95" />
                <line x1="16.95" y1="7.05" x2="19.78" y2="4.22" />
              </svg>
              <!-- Moon (dark) -->
              <svg
                v-else-if="opt.value === 'dark'"
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="seg__icon"
              >
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
              <!-- Monitor (auto) -->
              <svg
                v-else
                aria-hidden="true"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="seg__icon"
              >
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </label>
          </div>
        </div>

        <!-- Sound -->
        <div class="pref-row">
          <span class="pref-row__label">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="pref-row__icon"
            >
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
            </svg>
            {{ t("settings.sound") }}
          </span>
          <label class="switch" :class="{ 'switch--on': soundEnabled }">
            <input
              type="checkbox"
              class="switch__input"
              :checked="soundEnabled"
              :aria-label="soundEnabled ? t('settings.soundOn') : t('settings.soundOff')"
              @change="soundEnabled = !soundEnabled"
            >
            <span class="switch__thumb" aria-hidden="true" />
          </label>
        </div>
      </section>
    </div>
  </dialog>
</template>

<style scoped>
/* ─── Dialog shell ─── */
.settings-dialog {
  margin: auto;
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  width: min(420px, calc(100vw - 32px));
  max-height: min(640px, calc(100vh - 48px));
  padding: 0;
  overflow: hidden;
}
.settings-dialog[open] {
  display: flex;
  flex-direction: column;
}
.settings-dialog::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}

.settings-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1.5px dashed var(--color-ink);
  flex-shrink: 0;
}
.settings-dialog__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
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
.settings-expand-enter-active,
.settings-expand-leave-active {
  transition:
    opacity var(--motion-base) var(--ease-out),
    transform var(--motion-base) var(--ease-out);
}
.settings-expand-enter-from,
.settings-expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
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
  min-height: 40px;
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
