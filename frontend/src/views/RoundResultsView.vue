<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { disconnect } = useGameConnection();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

const countdown = ref(GAME_TIMINGS.ROUND_RESULTS_COUNTDOWN_S);
const leaveDialogOpen = ref(false);
let countdownInterval: number | null = null;

const currentScores = computed(() =>
  store.playersList.map((p) => ({ id: p.id, name: p.name, score: p.score })).sort((a, b) => b.score - a.score),
);

const resultsByPlayer = computed(() => {
  const grouped: Record<
    string,
    { targetName: string; correctGuesses: number; totalItems: number; pointsEarned: number }[]
  > = {};

  for (const result of store.lastRoundResults) {
    if (!grouped[result.playerId]) {
      grouped[result.playerId] = [];
    }

    const targetPlayer = store.players.get(result.targetPlayerId);
    const arr = grouped[result.playerId] as {
      targetName: string;
      correctGuesses: number;
      totalItems: number;
      pointsEarned: number;
    }[];
    arr.push({
      targetName: targetPlayer?.name || i18n.global.t("common.unknown"),
      correctGuesses: result.correctGuesses,
      totalItems: result.totalItems,
      pointsEarned: result.pointsEarned,
    });
  }

  return grouped;
});

const isLastRound = computed(() => store.currentRound >= store.maxRounds);

onMounted(() => {
  countdownInterval = window.setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(countdownInterval ?? undefined);
      countdownInterval = null;
    }
  }, 1000);
});

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
});

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    leaveRoom();
    return;
  }
  leaveDialogOpen.value = true;
}
</script>

<template>
  <div
    class="flex min-h-screen flex-col"
    style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)"
  >
    <header
      class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-black/25 px-6 py-3.5 backdrop-blur-md"
    >
      <h1 class="m-0 text-[1.375rem] font-extrabold text-white">
        {{ $t("roundResults.title", { round: store.currentRound }) }}
      </h1>
      <div class="flex items-center gap-3">
        <div
          class="flex items-center gap-1.5 rounded-full border border-white/30 bg-white/20 px-3.5 py-1.5 text-sm font-semibold text-white"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          {{ isLastRound ? $t("roundResults.finalResultsSoon") : $t("roundResults.nextRoundSoon") }}
          {{ $t("common.countdownIn", { count: countdown }) }}
        </div>
        <button
          type="button"
          class="btn-leave flex cursor-pointer items-center gap-1 rounded-md border-[1.5px] border-white/45 bg-white/15 px-3.5 py-2 text-sm font-semibold text-white transition-all hover:border-white/75 hover:bg-white/25"
          @click="showLeaveDialog"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          {{ $t("common.leave") }}
        </button>
      </div>
    </header>

    <div class="mx-auto flex w-full max-w-[1100px] flex-col gap-6 p-6 max-[768px]:p-4">
      <section>
        <h2 class="m-0 mb-3.5 text-lg font-bold tracking-wider text-white/95 uppercase">
          {{ $t("roundResults.roundPerformance") }}
        </h2>
        <div
          class="grid gap-4 max-[768px]:grid-cols-1"
          style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))"
        >
          <div v-for="player in store.playersList" :key="player.id" class="rounded-lg bg-white p-5 shadow-md">
            <h3 class="m-0 mb-3.5 border-b-2 border-primary pb-2 text-[1.0625rem] font-bold text-ink-dark">
              {{ player.name }}
            </h3>
            <div v-if="resultsByPlayer[player.id]" class="flex flex-col gap-2">
              <div
                v-for="(result, index) in resultsByPlayer[player.id]"
                :key="index"
                class="rounded-sm border-l-[3px] border-primary bg-surface px-3 py-2"
              >
                <span class="mb-1 block text-[0.8125rem] text-ink-muted">
                  {{ $t("roundResults.guessedPlayersDrawing", { name: result.targetName }) }}
                </span>
                <div class="flex items-center justify-between">
                  <span class="text-base font-bold text-ink-dark">
                    {{ result.correctGuesses }}/{{ result.totalItems }}
                  </span>
                  <span class="text-[0.9375rem] font-bold text-primary">
                    +{{ $t("common.pointsShort", { count: result.pointsEarned }) }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="m-0 py-2 text-sm text-ink-muted italic">{{ $t("roundResults.noGuessesSubmitted") }}</p>
          </div>
        </div>
      </section>

      <section>
        <h2 class="m-0 mb-3.5 text-lg font-bold tracking-wider text-white/95 uppercase">
          {{ $t("roundResults.currentStandings") }}
        </h2>
        <div class="flex flex-col gap-1.5 rounded-xl bg-white p-5 shadow-lg">
          <div
            v-for="(player, index) in currentScores"
            :key="player.id"
            class="flex items-center gap-3 rounded-md bg-surface px-4 py-3 text-base transition-transform"
            :class="[
              index === 0 && 'bg-gradient-to-br !from-[#ffd700] !to-[#ffed4e] font-bold',
              player.id === store.localPlayerId && 'border-2 border-primary !bg-indigo-50',
              index === 0 &&
                player.id === store.localPlayerId &&
                '!border-[#b8860b] bg-gradient-to-br !from-[#ffd700] !to-[#ffed4e]',
            ]"
          >
            <span
              class="rank min-w-6 text-[1.0625rem] font-extrabold"
              :class="index === 0 ? 'text-[#b8860b]' : 'text-primary'"
            >
              {{ index + 1 }}
            </span>
            <span class="flex-1 font-medium">{{ player.name }}</span>
            <span
              v-if="player.id === store.localPlayerId"
              class="rounded-full px-2 py-0.5 text-xs font-bold text-white"
              :class="index === 0 ? 'bg-[#b8860b]' : 'bg-primary'"
            >
              {{ $t("common.you") }}
            </span>
            <span class="font-bold" :class="index === 0 ? 'text-[#b8860b]' : 'text-primary'">
              {{ $t("common.pointsShort", { count: player.score }) }}
            </span>
          </div>
        </div>
      </section>
    </div>

    <ConfirmDialog
      v-model:open="leaveDialogOpen"
      :title="leaveDialog.title"
      :message="leaveDialog.message"
      :confirm-label="leaveDialog.confirmLabel"
      :cancel-label="leaveDialog.cancelLabel"
      variant="danger"
      @confirm="leaveRoom"
    />
  </div>
</template>
