<script setup lang="ts">
import { REACTION_EMOJI, REACTION_KEYS, type ReactionKey } from "@/composables/useReactions";
import { i18n } from "@/i18n";

/** Whose drawing the reactions are for; screen readers hear it with each button. */
defineProps<{ name: string }>();
defineEmits<{ react: [ReactionKey] }>();

const { t } = i18n.global;
const LABEL_KEYS: Record<ReactionKey, string> = {
  laugh: "reactions.laugh",
  shock: "reactions.shock",
  art: "reactions.art",
  "mind-blown": "reactions.mindBlown",
  think: "reactions.think",
};
</script>

<template>
  <!-- biome-ignore lint/a11y/useSemanticElements: role=group + aria-label names the reaction button cluster; no native element fits -->
  <div class="hd-rpad" role="group" :aria-label="t('reactions.group', { name })">
    <button
      v-for="k in REACTION_KEYS"
      :key="k"
      type="button"
      class="hd-rpad__btn"
      :aria-label="t('reactions.react', { reaction: t(LABEL_KEYS[k]), name })"
      @click="$emit('react', k)"
    >
      {{ REACTION_EMOJI[k] }}
    </button>
  </div>
</template>

<style scoped>
.hd-rpad {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}
.hd-rpad__btn {
  width: 44px;
  height: 44px;
  border-radius: 12px 16px 11px 14px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  box-shadow: 2px 2px 0 var(--color-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  cursor: pointer;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-rpad__btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
</style>
