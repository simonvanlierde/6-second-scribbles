<script setup lang="ts">
import { useI18n } from "vue-i18n";

import HdDialog from "@/components/ui/HdDialog.vue";

const open = defineModel<boolean>("open", { default: false });
const { t } = useI18n({ useScope: "global" });
</script>

<template>
  <HdDialog v-model:open="open" :title="t('settings.about')" :confirm-label="t('common.confirm')" variant="primary">
    <p class="about-text">
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
  </HdDialog>
</template>

<style scoped>
.about-text {
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
  line-height: 1.6;
  margin: 0 0 20px;
}
.about-text a {
  color: var(--color-ballpoint-blue);
  text-decoration: underline;
}
</style>
