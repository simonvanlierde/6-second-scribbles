<script setup lang="ts">
import { useClipboard } from "@vueuse/core";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import GameSettingsPanel from "@/components/GameSettingsPanel.vue";
import PlayerListPanel from "@/components/PlayerListPanel.vue";
import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { useNotifications } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { GAME_SETTINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const route = useRoute();
const router = useRouter();
const store = useGameStore();
const { t } = useI18n();
const { send, disconnect } = useGameConnection();
const { showNotification } = useNotifications();
const { copy } = useClipboard();

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

const leaveDialogOpen = ref(false);

const localPadVisible = computed({
  get: () => store.localPadVisible,
  set: (v: boolean) => {
    store.setLocalPadVisible(v);
  },
});

const roomCode = computed(() => route.params.roomCode as string);
const playerCount = computed(() => store.playersList.length);
const canStart = computed(() => store.canStartGame && store.isHost);

function handleClear() {
  if (store.isHost) {
    store.clearStrokes();
    send({ type: "drawpad_clear" });
  }
}

function toggleDrawpad() {
  localPadVisible.value = !localPadVisible.value;
}

function startGame() {
  if (!canStart.value) return;
  send({
    type: "start_game",
    difficulty: store.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
    rounds: store.maxRounds || GAME_SETTINGS.rounds.DEFAULT,
    drawingTimeLimit: store.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
    guessingTimeLimit: store.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
  });
}

async function copyRoomCode() {
  await copy(roomCode.value);
  showNotification("Copied!");
}

function showLeaveDialog() {
  leaveDialogOpen.value = true;
}

function confirmLeave() {
  leaveRoom();
}

function toggleRoomPadVisibility() {
  const visible = !store.roomPadVisible;
  store.setRoomPadVisible(visible);
  send({ type: "pad_visibility", visible });
}
</script>

<template>
  <div class="flex min-h-screen items-start justify-center p-5 pt-5">
    <div class="max-w-[1200px] w-full">
      <!-- Header -->
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          class="flex shrink-0 cursor-pointer items-center gap-1.5 rounded-md border-[1.5px] border-white/45 bg-white/15 px-3.5 py-2 text-sm font-semibold text-white transition-all hover:border-white/75 hover:bg-white/25"
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
          {{ $t('lobby.leaveRoom') }}
        </button>

        <button
          type="button"
          class="flex cursor-pointer items-center gap-2 rounded-md border-[1.5px] border-white/45 bg-white/20 px-4 py-2 transition-all hover:border-white hover:bg-white/30"
          title="Click to copy room code"
          @click="copyRoomCode"
        >
          🎨
          <span class="font-mono text-[1.2rem] font-bold tracking-widest text-white">{{ roomCode }}</span>
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
            class="shrink-0 text-white/70"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
      </div>

      <!-- Two-column layout -->
      <div class="grid items-start gap-5 max-[768px]:grid-cols-1 md:grid-cols-2">
        <!-- Left: Players + Settings + Start -->
        <div class="rounded-xl bg-white p-8 shadow-lg">
          <h2>{{ $t('lobby.players', { count: playerCount }) }}</h2>
          <PlayerListPanel />

          <div class="mt-2 border-t border-gray-200 pt-2"><GameSettingsPanel /></div>

          <div v-if="store.isHost" class="mt-4">
            <button
              type="button"
              class="w-full cursor-pointer rounded-md border-0 bg-gradient-to-br from-primary to-secondary px-4 py-3.5 text-[1.0625rem] font-bold text-white transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_6px_18px_rgba(102,126,234,0.4)] disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-none disabled:bg-gray-300 disabled:text-gray-500 disabled:shadow-none"
              :disabled="!canStart"
              @click="startGame"
            >
              {{ canStart ? $t('lobby.startGame') : $t('lobby.waitingForPlayers') }}
            </button>
          </div>
          <p
            v-else
            class="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3.5 text-center text-[0.9375rem] font-medium text-slate-700"
          >
            {{ playerCount >= 2 ? $t('lobby.waitingForHost') : $t('lobby.waitingForMore') }}
          </p>
        </div>

        <!-- Right: Drawpad -->
        <div v-if="store.isHost || store.roomPadVisible">
          <div class="flex flex-col gap-3 rounded-2xl bg-white p-5 shadow-[0_10px_40px_rgba(0,0,0,0.2)]">
            <div class="flex items-center justify-between">
              <h3 class="m-0 text-[1.0625rem] font-bold text-ink-dark">{{ $t('lobby.doodleTitle') }}</h3>
            </div>

            <div v-if="store.isHost" class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="cursor-pointer rounded border border-primary/25 bg-primary/10 px-2.5 py-1.5 text-[0.8125rem] font-semibold whitespace-nowrap text-primary-dark transition-all hover:bg-primary/20"
                @click="handleClear"
              >
                {{ $t('lobby.clearForAll') }}
              </button>
              <button
                type="button"
                class="cursor-pointer rounded border border-primary/25 bg-primary/10 px-2.5 py-1.5 text-[0.8125rem] font-semibold whitespace-nowrap text-primary-dark transition-all hover:bg-primary/20"
                @click="toggleRoomPadVisibility"
              >
                {{ store.roomPadVisible ? $t('lobby.hideForAll') : $t('lobby.showForAll') }}
              </button>
              <button
                v-if="store.roomPadVisible"
                type="button"
                class="cursor-pointer rounded border border-success/30 bg-success/10 px-2.5 py-1.5 text-[0.8125rem] font-semibold whitespace-nowrap text-success-dark transition-all hover:bg-success/20"
                @click="toggleDrawpad"
              >
                {{ localPadVisible ? $t('lobby.hideMyPad') : $t('lobby.showMyPad') }}
              </button>
            </div>
            <button
              v-else-if="!store.isHost"
              type="button"
              class="cursor-pointer rounded border border-success/30 bg-success/10 px-3 py-1.5 text-[0.8125rem] font-semibold whitespace-nowrap text-success-dark transition-all hover:bg-success/20"
              @click="toggleDrawpad"
            >
              {{ localPadVisible ? $t('lobby.hideMyPad') : $t('lobby.showMyPad') }}
            </button>

            <div v-if="store.roomPadVisible && localPadVisible" class="drawpad-canvas mt-1"><SharedDrawpad /></div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-model:open="leaveDialogOpen"
      :title="t('lobby.leaveDialogTitle')"
      :message="t('lobby.leaveDialogText')"
      :confirm-label="t('lobby.leave')"
      :cancel-label="t('lobby.cancel')"
      variant="danger"
      @confirm="confirmLeave"
    />
  </div>
</template>

<style scoped>
.drawpad-canvas :global(.mini-canvas) {
  height: 320px;
}
@media (max-width: 768px) {
  .drawpad-canvas :global(.mini-canvas) {
    height: 220px;
  }
}
</style>
