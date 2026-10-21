<script setup lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.vue";
import { AVATAR_COLOR_NAMES, AVATAR_COLORS, type AvatarColor } from "@/composables/useAvatar";
import { i18n } from "@/i18n";

const model = defineModel<AvatarColor>({ required: true });
defineProps<{ initial: string }>();
const { t } = i18n.global;
</script>

<template>
  <div class="avatar-picker" role="radiogroup" :aria-label="t('settings.avatarColor')">
    <button
      v-for="c in AVATAR_COLORS"
      :key="c"
      type="button"
      class="avatar-picker__btn"
      :class="{ 'avatar-picker__btn--active': c === model }"
      :aria-label="t(AVATAR_COLOR_NAMES[c])"
      v-bind="{ role: 'radio', 'aria-checked': c === model }"
      @click="model = c"
    >
      <HdAvatar :initial="initial" :color="c" size="md" />
    </button>
  </div>
</template>

<style scoped>
.avatar-picker {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.avatar-picker__btn {
  background: transparent;
  border: 0;
  padding: 4px;
  border-radius: 14px;
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring);
}
/* A fill, not an outline: the blue outline is the keyboard focus ring. */
.avatar-picker__btn--active {
  background: var(--color-highlighter-yellow);
  box-shadow: inset 0 0 0 2px var(--color-ink);
}
.avatar-picker__btn:active {
  transform: scale(0.94);
}
</style>
