<script setup lang="ts">
import { useI18n } from "vue-i18n";

import HdDialog from "@/components/ui/HdDialog.vue";

const open = defineModel<boolean>("open", { default: false });
const { t } = useI18n({ useScope: "global" });
</script>

<template>
  <HdDialog
    v-model:open="open"
    :title="t('home.howToPlay')"
    :confirm-label="t('common.confirm')"
    :cancel-label="t('common.cancel')"
    variant="primary"
    :message="''"
  >
    <ol class="htp">
      <li>{{ t('home.step1', { count: 10 }) }}</li>
      <li>{{ t('home.step2', { time: 60 }) }}</li>
      <li>{{ t('home.step3') }}</li>
      <li>{{ t('home.step4') }}</li>
    </ol>
  </HdDialog>
</template>

<style scoped>
.htp {
  margin: 0 0 16px;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  line-height: 1.5;
}
</style>
