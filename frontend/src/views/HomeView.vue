<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import CreateJoinCard from "@/components/CreateJoinCard.vue";
import HomePlayerPreferences from "@/components/HomePlayerPreferences.vue";
import HowToPlay from "@/components/HowToPlay.vue";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { fetchLocaleAvailability, localeOptions } = useLocaleAvailability();

const playerLocale = computed({
  get: () => store.localPlayerLocale,
  set: (value: string) => {
    store.setLocalPlayerLocale(value);
  },
});

const playerName = computed(() => store.localPlayerName);
const openNameEditorSignal = ref(0);

function openNameEditor() {
  openNameEditorSignal.value += 1;
}

onMounted(() => {
  void fetchLocaleAvailability();
});

watch(
  localeOptions,
  (options) => {
    const selected = options.find((option) => option.code === playerLocale.value);
    if (selected?.enabled) return;
    const fallback = options.find((option) => option.enabled);
    if (fallback) store.setLocalPlayerLocale(fallback.code);
  },
  { immediate: true },
);
</script>

<template>
  <div class="min-h-screen px-5 py-5 md:py-6 lg:px-6 lg:py-7">
    <div class="mx-auto w-full max-w-[1180px]">
      <div class="mb-4 text-center md:mb-5 lg:mb-6">
        <h1 class="mb-0 text-[2.8rem] leading-[0.98] md:text-[3.4rem] lg:text-[4rem]">🎨 {{ $t('home.title') }}</h1>
      </div>

      <div class="flex flex-col gap-4 lg:gap-5">
        <CreateJoinCard :open-name-editor-signal="openNameEditorSignal" />
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start lg:gap-5">
          <HomePlayerPreferences
            v-model="playerLocale"
            :player-name="playerName"
            :locale-options="localeOptions"
            @edit-name="openNameEditor"
          />
          <HowToPlay />
        </div>
      </div>

      <footer class="mt-4 pb-4 text-[0.78rem] leading-relaxed text-white/65 lg:mt-5">
        <div class="text-center [&_a]:text-white/85 [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-white">
          <p class="leading-relaxed">
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
        </div>
      </footer>
    </div>
  </div>
</template>
