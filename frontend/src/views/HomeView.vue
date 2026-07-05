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
      <svg class="home-underline" viewBox="0 0 300 18" fill="none" aria-hidden="true" preserveAspectRatio="none">
        <path
          d="M4 12 C 46 4, 96 16, 150 10 S 250 4, 296 12"
          stroke="var(--color-marker-red)"
          stroke-width="5"
          stroke-linecap="round"
        />
      </svg>
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
  min-height: 100svh;
  max-width: 560px;
  margin: 0 auto;
  padding: 32px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 24px;
  position: relative;
  z-index: 1;
}
.home-hero {
  text-align: center;
}
.home-wordmark {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(40px, 8vw, 56px);
  line-height: 1;
  margin: 0;
  color: var(--color-ink);
}
/* The marker underline draws itself in on load — the one signature moment,
   embodying "doodle" before the player has done anything. */
.home-underline {
  display: block;
  width: min(300px, 70%);
  height: 16px;
  margin: 6px auto 10px;
}
.home-underline path {
  stroke-dasharray: 340;
  stroke-dashoffset: 340;
  animation: home-draw 900ms var(--ease-out) 200ms forwards;
}
@keyframes home-draw {
  to {
    stroke-dashoffset: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .home-underline path {
    animation: none;
    stroke-dashoffset: 0;
  }
}
.home-tagline {
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  color: var(--color-ink-muted);
  margin: 0;
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
