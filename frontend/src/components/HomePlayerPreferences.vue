<script setup lang="ts">
import { ref } from "vue";

import LocaleSelector from "@/components/LocaleSelector.vue";
import { formatLocaleLabel, type LocaleOption } from "@/shared/locales";

defineProps<{
  playerName: string;
  localeOptions: LocaleOption[];
}>();

const playerLocale = defineModel<string>({ required: true });

const emit = defineEmits<{
  editName: [];
}>();

const isOpen = ref(false);
</script>

<template>
  <section
    class="overflow-hidden rounded-2xl bg-white/95 shadow-[0_5px_20px_rgba(0,0,0,0.1)]"
    data-testid="home-player-preferences"
  >
    <button
      type="button"
      class="flex w-full cursor-pointer items-center justify-between gap-4 border-0 bg-transparent px-6 py-4 text-left hover:bg-black/[0.03]"
      data-testid="home-player-preferences-toggle"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <span class="flex min-w-0 items-center gap-3 md:gap-4">
        <span class="shrink-0 text-base font-bold text-ink-dark">{{ $t("common.you") }}</span>
        <span class="min-w-0 truncate text-sm text-slate-500 md:text-[0.9375rem]">
          {{ `${playerName.trim() || $t("home.enterYourName")} · ${formatLocaleLabel(playerLocale)}` }}
        </span>
      </span>
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
      <div v-if="isOpen" class="border-t border-slate-100 px-6 pt-4 pb-5">
        <div class="flex flex-col gap-4 md:grid md:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] md:items-start md:gap-4">
          <div class="min-w-0">
            <p class="m-0 text-xs font-semibold tracking-[0.08em] text-slate-400 uppercase">
              {{ $t("home.yourName") }}
            </p>
            <div class="mt-2 flex items-center gap-3">
              <button
                type="button"
                class="inline-flex h-[4.5rem] w-full min-w-0 max-w-full items-center gap-3 rounded-full border border-slate-200/90 bg-white px-3 py-2.5 text-left shadow-[0_6px_18px_rgba(15,23,42,0.06)] transition-[transform,box-shadow,border-color] hover:-translate-y-px hover:border-slate-300 hover:shadow-[0_10px_22px_rgba(15,23,42,0.1)]"
                data-testid="player-name-chip"
                @click="emit('editName')"
              >
                <span
                  class="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary/16 to-secondary/16 text-base font-bold text-primary"
                >
                  {{ playerName.trim() ? playerName.trim().charAt(0).toUpperCase() : "?" }}
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-[0.98rem] font-semibold text-slate-800">
                    {{ playerName.trim() || $t("home.enterYourName") }}
                  </span>
                </span>
                <span class="text-slate-400" aria-hidden="true">✎</span>
              </button>
            </div>
          </div>

          <div class="min-w-0">
            <p class="m-0 text-xs font-semibold tracking-[0.08em] text-slate-400 uppercase">
              {{ $t("home.language") }}
            </p>
            <div class="mt-2">
              <LocaleSelector
                id="player-locale-card"
                v-model="playerLocale"
                :options="localeOptions"
                variant="pill"
                class-name="pill-light"
              />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </section>
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
