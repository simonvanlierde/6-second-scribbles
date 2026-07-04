<script setup lang="ts">
import { computed } from "vue";

import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { leaveRoom } = useLeaveRoom();

const drawings = computed(() => store.playersList.filter((player) => player.drawing));
// RoomView only renders this view outside the lobby, so no lobby label is needed.
const phaseLabel = computed(() => {
  if (store.gamePhase === "drawing") return i18n.global.t("spectator.drawingRound");
  if (store.gamePhase === "guessing") return i18n.global.t("spectator.guessingRound");
  if (store.gamePhase === "round_results") return i18n.global.t("spectator.roundResults");
  if (store.gamePhase === "final_results") return i18n.global.t("spectator.finalResults");
  return i18n.global.t("spectator.watchingRoom");
});
</script>

<template>
  <div
    class="grid min-h-screen gap-4 p-6 text-white"
    style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)"
  >
    <header
      class="mx-auto flex w-full max-w-[1100px] items-start justify-between gap-4 rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <div>
        <p class="m-0 mb-2 text-xs tracking-widest text-white/70 uppercase">
          {{ $t("common.roomCode", { code: store.roomCode }) }}
        </p>
        <h1 class="m-0">{{ phaseLabel }}</h1>
        <p class="m-0 mt-2 text-white/80">{{ $t("spectator.watchingLive") }}</p>
      </div>
      <div class="flex flex-wrap justify-end gap-3">
        <button
          type="button"
          class="leave-btn cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
          @click="leaveRoom"
        >
          {{ $t("spectator.leaveRoom") }}
        </button>
      </div>
    </header>

    <section
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">{{ $t("spectator.players") }}</h2>
      <div class="mt-3 flex flex-wrap gap-2">
        <div
          v-for="player in store.playersList"
          :key="player.id"
          class="flex items-center gap-2 rounded-full bg-white/10 px-3 py-2"
        >
          {{ player.name }}
          <span class="text-sm text-white/70">{{ $t("common.pointsShort", { count: player.score }) }}</span>
        </div>
      </div>
    </section>

    <section
      v-if="store.gamePhase === 'drawing'"
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">{{ $t("spectator.drawings") }}</h2>
      <div
        v-if="drawings.length"
        class="mt-3 grid gap-3"
        style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))"
      >
        <article
          v-for="player in drawings"
          :key="player.id"
          class="overflow-hidden rounded-2xl border border-white/10 bg-white/5"
        >
          <img
            :src="player.drawing"
            :alt="$t('spectator.drawingAlt', { name: player.name })"
            class="block h-[180px] w-full bg-black/15 object-contain"
          >
          <p class="p-3 text-white/85">{{ player.name }}</p>
        </article>
      </div>
      <p v-else class="p-3 text-white/85">{{ $t("spectator.noDrawingsYet") }}</p>
    </section>

    <section
      v-else
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">{{ $t("spectator.roundStatus") }}</h2>
      <p v-if="store.gamePhase === 'guessing'" class="p-3 text-white/85">{{ $t("spectator.guessingInProgress") }}</p>
      <p v-else class="p-3 text-white/85">{{ $t("spectator.betweenRounds") }}</p>
    </section>
  </div>
</template>
