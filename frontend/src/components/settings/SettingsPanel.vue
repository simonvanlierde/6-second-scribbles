<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import LocaleSelector from "@/components/LocaleSelector.vue";
import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import HdSegmented from "@/components/ui/HdSegmented.vue";
import HdSidepanel from "@/components/ui/HdSidepanel.vue";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { useSettingsPanel } from "@/composables/useSettingsPanel";
import { useSound } from "@/composables/useSound";
import { type Theme, useTheme } from "@/composables/useTheme";
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
        <HdButton variant="secondary" @click="soundEnabled = !soundEnabled"> {{ t("settings.toggle") }} </HdButton>
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
