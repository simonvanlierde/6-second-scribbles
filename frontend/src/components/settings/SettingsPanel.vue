<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";
import HdInput from "@/components/ui/HdInput.vue";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { useSettingsPanel } from "@/composables/useSettingsPanel";
import { useSound } from "@/composables/useSound";
import { type Theme, useTheme } from "@/composables/useTheme";
import { formatLocaleLabel } from "@/shared/locales";
import { useGameStore } from "@/stores/game";

const open = defineModel<boolean>("open", { default: false });

const store = useGameStore();
const { theme } = useTheme();
const { enabled: soundEnabled } = useSound();
const { focusNameOnOpen } = useSettingsPanel();
const nameInputRef = ref<InstanceType<typeof HdInput> | null>(null);
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

watch(focusNameOnOpen, (v) => {
  if (v) {
    nextTick(() => {
      nameInputRef.value?.focus();
      focusNameOnOpen.value = false;
    });
  }
});

const { localeOptions, fetchLocaleAvailability } = useLocaleAvailability();
const { t } = useI18n({ useScope: "global" });

onMounted(() => {
  void fetchLocaleAvailability();
});

function close() {
  open.value = false;
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
  get: () => store.localPlayerColor,
  set: (v) => store.setLocalPlayerColor(v),
});
const initial = computed(() => getAvatarInitial(playerName.value || "?"));

// Avatar color picker
const colorPickerOpen = ref(false);

// Locale dropdown
const localeOpen = ref(false);
const localeWrapperRef = ref<HTMLElement | null>(null);

function toggleLocale() {
  themeOpen.value = false;
  localeOpen.value = !localeOpen.value;
}
function selectLocale(code: string) {
  playerLocale.value = code;
  localeOpen.value = false;
}
function handleLocaleBlur(e: FocusEvent) {
  if (!localeWrapperRef.value?.contains(e.relatedTarget as Node | null)) {
    localeOpen.value = false;
  }
}

// Theme dropdown
const themeOpen = ref(false);
const themeWrapperRef = ref<HTMLElement | null>(null);

const themeOptions = computed<Array<{ value: Theme; label: string }>>(() => [
  { value: "light", label: t("settings.themeLight") },
  { value: "dark", label: t("settings.themeDark") },
  { value: "auto", label: t("settings.themeAuto") },
]);
const currentThemeLabel = computed(
  () => themeOptions.value.find((o) => o.value === theme.value)?.label ?? t("settings.themeAuto"),
);

function toggleTheme() {
  localeOpen.value = false;
  themeOpen.value = !themeOpen.value;
}
function selectTheme(value: Theme) {
  theme.value = value;
  themeOpen.value = false;
}
function handleThemeBlur(e: FocusEvent) {
  if (!themeWrapperRef.value?.contains(e.relatedTarget as Node | null)) {
    themeOpen.value = false;
  }
}
</script>

<template>
  <dialog ref="dialogRef" class="settings-dialog" @click.self="close" @close="close">
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
            ref="nameInputRef"
            v-model="playerName"
            :aria-label="t('settings.yourName')"
            :placeholder="t('settings.namePlaceholder')"
          />
        </div>
        <Transition name="settings-expand">
          <div v-if="colorPickerOpen" class="avatar-colors">
            <AvatarColorPicker v-model="playerColor" :initial="initial" />
          </div>
        </Transition>
      </section>

      <!-- Language · Theme · Sound — one row -->
      <section class="settings-section settings-controls-row">
        <!-- Locale -->
        <div ref="localeWrapperRef" class="ctrl" @focusout="handleLocaleBlur">
          <button
            type="button"
            class="ctrl__btn"
            :aria-expanded="localeOpen"
            :aria-label="t('settings.language')"
            @click="toggleLocale"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__icon"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            <span class="ctrl__label">{{ formatLocaleLabel(playerLocale) }}</span>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__chevron"
              :class="{ 'ctrl__chevron--open': localeOpen }"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div
            v-show="localeOpen"
            class="ctrl__dropdown ctrl__dropdown--scroll"
            role="listbox"
            :aria-label="t('settings.language')"
          >
            <button
              v-for="opt in localeOptions"
              :key="opt.code"
              type="button"
              class="ctrl__option"
              :class="{ 'ctrl__option--active': playerLocale === opt.code, 'ctrl__option--disabled': !opt.enabled }"
              :disabled="!opt.enabled"
              @click="selectLocale(opt.code)"
            >
              {{ formatLocaleLabel(opt.code) }}
            </button>
          </div>
        </div>

        <div class="ctrl-sep" aria-hidden="true" />

        <!-- Theme -->
        <div ref="themeWrapperRef" class="ctrl" @focusout="handleThemeBlur">
          <button
            type="button"
            class="ctrl__btn"
            :aria-expanded="themeOpen"
            :aria-label="t('settings.theme')"
            @click="toggleTheme"
          >
            <!-- Sun (light) -->
            <svg
              v-if="theme === 'light'"
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__icon"
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
              v-else-if="theme === 'dark'"
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__icon"
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
              class="ctrl__icon"
            >
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
            <span class="ctrl__label">{{ currentThemeLabel }}</span>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__chevron"
              :class="{ 'ctrl__chevron--open': themeOpen }"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div v-show="themeOpen" class="ctrl__dropdown" role="listbox" :aria-label="t('settings.theme')">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              type="button"
              class="ctrl__option"
              :class="{ 'ctrl__option--active': theme === opt.value }"
              @click="selectTheme(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div class="ctrl-sep" aria-hidden="true" />

        <!-- Sound -->
        <div class="ctrl">
          <button
            type="button"
            class="ctrl__btn"
            :aria-label="soundEnabled ? t('settings.soundOn') : t('settings.soundOff')"
            :aria-pressed="soundEnabled"
            @click="soundEnabled = !soundEnabled"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="ctrl__icon"
            >
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <template v-if="soundEnabled">
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              </template>
              <template v-else>
                <line x1="23" y1="9" x2="17" y2="15" />
                <line x1="17" y1="9" x2="23" y2="15" />
              </template>
            </svg>
            <span class="ctrl__label">{{ soundEnabled ? t("settings.soundOn") : t("settings.soundOff") }}</span>
          </button>
        </div>
      </section>

      <!-- About -->
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
    </div>
  </dialog>
</template>

<style scoped>
/* ─── Dialog shell ─── */
.settings-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  width: min(420px, calc(100vw - 32px));
  max-height: min(640px, calc(100vh - 48px));
  margin: 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.settings-dialog::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}

/* On narrow screens: bottom sheet */
@media (max-width: 500px) {
  .settings-dialog {
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    transform: none;
    width: 100%;
    max-width: 100%;
    max-height: 88vh;
    border-radius: 22px 22px 0 0;
  }
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

/* ─── Controls row (language · theme · sound) ─── */
.settings-controls-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  overflow: visible;
}

.ctrl {
  flex: 1;
  min-width: 0;
  position: relative;
}

.ctrl-sep {
  width: 1px;
  height: 20px;
  background: var(--color-ink);
  opacity: 0.2;
  flex-shrink: 0;
  margin: 0 4px;
}

.ctrl__btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: 0;
  padding: 4px 2px;
  width: 100%;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
  min-height: 36px;
}

.ctrl__icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: var(--color-ink);
}

.ctrl__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.ctrl__chevron {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  opacity: 0.6;
  transition: transform var(--motion-fast) var(--ease-out);
}
.ctrl__chevron--open {
  transform: rotate(180deg);
}

.ctrl__dropdown {
  position: absolute;
  left: 0;
  top: calc(100% + 4px);
  z-index: 30;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  min-width: 120px;
}
.ctrl__dropdown--scroll {
  max-height: 220px;
  overflow-y: auto;
}

.ctrl__option {
  display: block;
  width: 100%;
  background: transparent;
  border: 0;
  border-bottom: 1px dashed color-mix(in srgb, var(--color-ink) 20%, transparent);
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
  line-height: 1.2;
}
.ctrl__option:last-child {
  border-bottom: 0;
}
.ctrl__option:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-ink) 8%, transparent);
}
.ctrl__option--active {
  font-weight: 700;
}
.ctrl__option--disabled {
  opacity: 0.38;
  cursor: default;
}

/* ─── About ─── */
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
