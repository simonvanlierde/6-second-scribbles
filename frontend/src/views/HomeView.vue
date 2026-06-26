<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";

import AboutDialog from "@/components/home/AboutDialog.vue";
import HomeCreateJoin from "@/components/home/HomeCreateJoin.vue";
import HowToPlayDialog from "@/components/home/HowToPlayDialog.vue";

const { t } = useI18n();
const howOpen = ref(false);
const aboutOpen = ref(false);
</script>

<template>
  <div class="home-page">
    <header class="home-hero">
      <h1 class="home-wordmark">{{ t("home.title") }}</h1>
      <p class="home-tagline">{{ t("home.tagline") }}</p>
    </header>

    <main class="home-main"><HomeCreateJoin /></main>

    <footer class="home-footer">
      <button type="button" class="home-footer__link" @click="howOpen = true">{{ t("home.howToPlay") }}</button>
      <span class="home-footer__sep" aria-hidden="true">·</span>
      <button type="button" class="home-footer__link" @click="aboutOpen = true">{{ t("settings.about") }}</button>
    </footer>

    <HowToPlayDialog v-model:open="howOpen" />
    <AboutDialog v-model:open="aboutOpen" />
  </div>
</template>

<style scoped>
.home-page {
  max-width: 560px;
  margin: 0 auto;
  padding: 48px 20px 96px;
  position: relative;
  z-index: 1;
}
.home-hero {
  text-align: center;
  margin-bottom: 32px;
}
.home-wordmark {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(40px, 8vw, 56px);
  line-height: 1;
  margin: 0 0 8px;
  color: var(--color-ink);
}
.home-tagline {
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  color: var(--color-ink-muted);
  margin: 0;
}
.home-main {
  margin-bottom: 24px;
}
.home-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.home-footer__link {
  background: transparent;
  border: 0;
  color: var(--color-ballpoint-blue);
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  text-decoration: underline wavy;
  text-underline-offset: 4px;
  cursor: pointer;
  padding: 8px 12px;
}
.home-footer__sep {
  color: var(--color-ink-muted);
  font-size: var(--text-body-md);
  user-select: none;
}
</style>
