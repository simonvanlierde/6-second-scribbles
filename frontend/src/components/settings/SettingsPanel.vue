<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdSegmented from "@/components/ui/HdSegmented.vue";
import HdSidepanel from "@/components/ui/HdSidepanel.vue";
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

const themeOptions = computed<Array<{ value: Theme; label: string }>>(() => [
  { value: "light", label: t("settings.themeLight") },
  { value: "dark", label: t("settings.themeDark") },
  { value: "auto", label: t("settings.themeAuto") },
]);
</script>

<template>
  <HdSidepanel v-model:open="open" :title="t('settings.title')">
    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.identity") }}</h3>
      <div class="settings-identity">
        <HdAvatar :initial="initial" :color="playerColor" size="lg" />
        <HdInput
          ref="nameInputRef"
          v-model="playerName"
          :aria-label="t('settings.yourName')"
          :placeholder="t('settings.namePlaceholder')"
        />
      </div>
      <AvatarColorPicker v-model="playerColor" :initial="initial" />
    </section>

    <section class="settings-section settings-section--row">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="settings-icon"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      <select v-model="playerLocale" class="settings-locale-select" :aria-label="t('settings.language')">
        <option v-for="opt in localeOptions" :key="opt.code" :value="opt.code" :disabled="!opt.enabled">
          {{ formatLocaleLabel(opt.code) }}
        </option>
      </select>
    </section>

    <section class="settings-section">
      <h3 class="settings-section__title">{{ t("settings.theme") }}</h3>
      <HdSegmented v-model="theme" :options="themeOptions" name="ds-theme" :aria-label="t('settings.theme')" />
    </section>

    <section class="settings-section settings-section--row">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="settings-icon"
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
      <button
        type="button"
        class="settings-sound-toggle"
        :aria-label="soundEnabled ? t('settings.soundOn') : t('settings.soundOff')"
        :aria-pressed="soundEnabled"
        @click="soundEnabled = !soundEnabled"
      >
        {{ soundEnabled ? t('settings.soundOn') : t('settings.soundOff') }}
      </button>
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
.settings-section--row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px dashed var(--color-ink);
}
.settings-section--row:last-child {
  border-bottom: 0;
}
.settings-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: var(--color-ink);
}
.settings-sound-toggle {
  background: transparent;
  border: 0;
  padding: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.settings-locale-select {
  appearance: none;
  -webkit-appearance: none;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  color: var(--color-ink);
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  padding: 6px 12px;
  box-shadow: var(--shadow-pill);
  cursor: pointer;
  flex: 1;
}
.settings-locale-select:focus {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
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
