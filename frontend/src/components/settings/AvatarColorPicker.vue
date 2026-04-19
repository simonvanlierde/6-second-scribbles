<script setup lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.vue";
import { AVATAR_COLORS, type AvatarColor } from "@/composables/useAvatar";

interface Props {
  modelValue: AvatarColor;
  initial: string;
}

defineProps<Props>();
const emit = defineEmits<{ "update:modelValue": [AvatarColor] }>();

function pick(c: AvatarColor): void {
  emit("update:modelValue", c);
}
</script>

<template>
  <div class="avatar-picker" role="radiogroup" aria-label="Avatar color">
    <button
      v-for="c in AVATAR_COLORS"
      :key="c"
      type="button"
      class="avatar-picker__btn"
      :class="{ 'avatar-picker__btn--active': c === modelValue }"
      v-bind="{ role: 'radio', 'aria-checked': c === modelValue }"
      @click="pick(c)"
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
.avatar-picker__btn--active {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.avatar-picker__btn:active {
  transform: scale(0.94);
}
</style>
