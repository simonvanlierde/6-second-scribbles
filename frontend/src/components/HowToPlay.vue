<script setup lang="ts">
import { ref } from "vue";

const isOpen = ref(false);
</script>

<template>
  <div class="overflow-hidden rounded-2xl bg-white/95 shadow-[0_5px_20px_rgba(0,0,0,0.1)]">
    <button
      type="button"
      class="flex w-full cursor-pointer items-center justify-between border-0 bg-transparent px-6 py-4 text-base font-bold text-ink-dark hover:bg-black/[0.03]"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <span>{{ $t('home.howToPlay') }}</span>
      <svg
        class="shrink-0 text-primary transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <Transition name="collapse">
      <div v-if="isOpen" class="px-6 pt-1 pb-5">
        <ol class="flex list-none flex-col gap-3">
          <li
            v-for="(n, i) in [1, 2, 3, 4]"
            :key="n"
            class="flex items-start gap-3.5 text-[0.9375rem] leading-relaxed text-slate-700"
          >
            <span
              class="mt-0.5 flex h-[1.625rem] w-[1.625rem] shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-xs font-bold text-white"
            >
              {{ n }}
            </span>
            <span v-if="i === 0">{{ $t('home.step1', { count: 10 }) }}</span>
            <span v-else-if="i === 1">{{ $t('home.step2', { time: 60 }) }}</span>
            <span v-else-if="i === 2">{{ $t('home.step3') }}</span>
            <span v-else>{{ $t('home.step4') }}</span>
          </li>
        </ol>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}
.collapse-enter-to,
.collapse-leave-from {
  max-height: 300px;
  opacity: 1;
}
</style>
