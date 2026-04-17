<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { send, disconnect } = useGameConnection();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();
const isReady = ref(false);
const autoRestartTimeout = ref<number | null>(null);
const leaveDialogOpen = ref(false);

const finalScores = computed(() => store.getFinalScores());

const rankedScores = computed(() => {
  const scores = finalScores.value;
  const ranked: Array<
    (typeof scores)[number] & {
      rank: number;
      isTied: boolean;
    }
  > = [];

  let index = 0;
  while (index < scores.length) {
    const score = scores[index]?.score ?? 0;
    let groupEnd = index + 1;
    while (groupEnd < scores.length && scores[groupEnd]?.score === score) {
      groupEnd += 1;
    }
    const rank = index + 1;
    const isTied = groupEnd - index > 1;
    for (let i = index; i < groupEnd; i += 1) {
      const player = scores[i];
      if (!player) continue;
      ranked.push({ ...player, rank, isTied });
    }
    index = groupEnd;
  }

  return ranked;
});

const winners = computed(() => rankedScores.value.filter((player) => player.rank === 1));
const winnerHeading = computed(() => (winners.value.length > 1 ? "Winners" : "Winner"));
const winnerNames = computed(() => formatNames(winners.value.map((player) => player.playerName)));
const winnerScoreText = computed(() =>
  winners.value.length > 1
    ? `Tied at ${winners.value[0]?.score ?? 0} points`
    : `${winners.value[0]?.score ?? 0} points`,
);

function formatNames(names: string[]) {
  if (names.length <= 1) return names[0] || "Unknown";
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return names.join(", ");
}

function formatOrdinal(rank: number) {
  const remainder100 = rank % 100;
  if (remainder100 >= 11 && remainder100 <= 13) return `${rank}th`;
  const remainder10 = rank % 10;
  if (remainder10 === 1) return `${rank}st`;
  if (remainder10 === 2) return `${rank}nd`;
  if (remainder10 === 3) return `${rank}rd`;
  return `${rank}th`;
}

watch(
  () => store.gamePhase,
  (newPhase) => {
    if (newPhase === "lobby") clearAutoRestartTimeout();
  },
);

watch(
  () => store.readyCount,
  (newReadyCount) => {
    if (!store.isHost) return;
    if (newReadyCount > 0 && newReadyCount === store.totalPlayers) {
      clearAutoRestartTimeout();
      autoRestartTimeout.value = window.setTimeout(() => {
        playAgain();
      }, GAME_TIMINGS.AUTO_RESTART_TIMEOUT_MS);
    }
  },
);

function clearAutoRestartTimeout() {
  if (autoRestartTimeout.value) {
    clearTimeout(autoRestartTimeout.value);
    autoRestartTimeout.value = null;
  }
}

function playAgain() {
  if (store.isHost) {
    send({ type: "restart_game" });
    store.resetRound();
    store.gamePhase = "lobby";
  } else {
    isReady.value = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
  }
}

function leaveRoom() {
  clearAutoRestartTimeout();
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    leaveRoom();
    return;
  }
  leaveDialogOpen.value = true;
}

onUnmounted(() => {
  clearAutoRestartTimeout();
});
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-5">
    <div class="max-w-[1200px] w-full">
      <h1>{{ $t('results.gameOver') }}</h1>

      <div class="mb-8 rounded-xl bg-gradient-to-br from-primary to-secondary p-8 text-center text-white shadow-lg">
        <div class="mb-4 animate-bounce text-6xl">🎉</div>
        <h2 class="my-2 text-3xl">{{ winnerHeading }}: {{ winnerNames }}</h2>
        <p class="m-0 text-2xl font-bold">{{ winnerScoreText }}</p>
      </div>

      <div class="mb-8 rounded-xl bg-white p-8 shadow-lg">
        <h2>{{ $t('results.finalScores') }}</h2>
        <div class="my-6">
          <div
            v-for="player in rankedScores"
            :key="player.playerId"
            class="my-2 flex items-center justify-between gap-4 rounded-lg bg-surface p-4 text-[1.125rem] transition-transform hover:translate-x-1"
            :class="{
              winner: player.rank === 1,
              tied: player.isTied,
              '!bg-gradient-to-br !from-[#ffd89b] !to-[#19547b] !text-white !text-2xl !font-bold': player.rank === 1,
              '!border-2 !border-[#3498db] !bg-[#e3f2fd]': player.playerId === store.localPlayerId && player.rank !== 1,
            }"
          >
            <div
              class="rank flex h-10 w-10 items-center justify-center rounded-full bg-gray-300 text-lg font-bold"
              :class="[
                player.rank === 1 && '!bg-white text-[#ffd700]',
                player.isTied && player.rank !== 1 && '!bg-orange-400 !text-white',
              ]"
            >
              {{ player.rank }}
            </div>
            <div class="flex flex-1 items-center gap-2">
              <span class="text-lg">{{ player.playerName }}</span>
              <span
                v-if="player.playerId === store.localPlayerId"
                class="rounded bg-gray-200 px-2 py-1 text-xs text-gray-600"
              >
                {{ $t('results.you') }}
              </span>
              <span v-if="player.isTied" class="rounded bg-blue-100 px-2 py-1 text-xs text-blue-800">
                {{ $t('results.tiedForRank', { rank: formatOrdinal(player.rank) }) }}
              </span>
            </div>
            <div class="text-xl font-bold text-slate-800">{{ $t('results.pts', { score: player.score }) }}</div>
          </div>
        </div>

        <div class="my-6 text-center">
          <p class="m-0 rounded bg-gray-50 p-3 text-lg font-semibold text-slate-700">
            {{ $t('results.playersReady', { count: store.readyCount, total: store.totalPlayers }) }}
          </p>
        </div>

        <div
          class="mt-8 flex flex-wrap items-center justify-center gap-4 max-[768px]:flex-col max-[768px]:[&_button]:w-full"
        >
          <button
            v-if="store.isHost"
            type="button"
            class="cursor-pointer rounded-md border-0 bg-primary py-3.5 px-6 text-base font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-primary-dark hover:shadow-[0_4px_12px_rgba(102,126,234,0.4)] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
            @click="playAgain"
          >
            {{ $t('results.playAgain') }}
          </button>
          <button
            v-else-if="!isReady"
            type="button"
            class="cursor-pointer rounded-md border-0 bg-primary py-3.5 px-6 text-base font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-primary-dark hover:shadow-[0_4px_12px_rgba(102,126,234,0.4)] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
            @click="playAgain"
          >
            {{ $t('results.readyForNext') }}
          </button>
          <div
            v-else
            class="max-w-[400px] flex-1 rounded border-2 border-green-200 bg-green-100 px-6 py-3 text-center text-base font-medium text-green-900"
          >
            {{ $t('results.readyWaiting') }}
          </div>
          <button
            type="button"
            class="cursor-pointer rounded-md border-0 bg-success py-3.5 px-6 text-base font-semibold text-white transition-all hover:bg-success-dark"
            @click="showLeaveDialog"
          >
            {{ $t('results.leaveRoom') }}
          </button>
        </div>
      </div>

      <div class="mt-8 rounded-xl bg-white p-8 shadow-lg">
        <h3 class="mt-0 mb-6 text-center">{{ $t('results.gameStatistics') }}</h3>
        <div class="grid gap-6" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))">
          <div class="rounded-lg bg-gray-50 p-4 text-center">
            <div class="mb-2 text-sm text-gray-600">{{ $t('results.totalRounds') }}</div>
            <div class="text-2xl font-bold text-slate-800">{{ store.maxRounds }}</div>
          </div>
          <div class="rounded-lg bg-gray-50 p-4 text-center">
            <div class="mb-2 text-sm text-gray-600">{{ $t('results.players') }}</div>
            <div class="text-2xl font-bold text-slate-800">{{ store.playersList.length }}</div>
          </div>
          <div class="rounded-lg bg-gray-50 p-4 text-center">
            <div class="mb-2 text-sm text-gray-600">{{ $t('results.difficulty') }}</div>
            <div class="text-2xl font-bold text-slate-800 capitalize">{{ store.difficulty }}</div>
          </div>
        </div>
      </div>
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
