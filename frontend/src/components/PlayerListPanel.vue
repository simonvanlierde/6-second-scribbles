<script setup lang="ts">
import { computed, ref } from "vue";

import { useGameConnection } from "@/composables/useGameConnection";
import { formatLocaleLabel } from "@/shared/locales";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();

const showKickConfirm = ref<string | null>(null);

const activeKickVotes = computed(() => store.kickVotes);

function canKickPlayer(playerId: string): boolean {
  return playerId !== store.localPlayerId;
}

function initiateKick(targetPlayerId: string) {
  showKickConfirm.value = targetPlayerId;
}

function confirmKick(targetPlayerId: string) {
  send({ type: "initiate_kick", targetPlayerId });
  showKickConfirm.value = null;
}

function cancelKick() {
  showKickConfirm.value = null;
}

function voteToKick(targetPlayerId: string) {
  send({ type: "cast_kick_vote", targetPlayerId });
}

const targetPlayerName = computed(() => store.playersList.find((p) => p.id === showKickConfirm.value)?.name);
const targetIsHost = computed(() => store.playersList.find((p) => p.id === showKickConfirm.value)?.id === store.hostId);
</script>

<template>
  <div>
    <div
      v-if="!store.isHost"
      class="my-4 flex items-center gap-2 rounded border border-gray-300 bg-gray-50 p-3 text-[0.95rem]"
    >
      <span class="font-semibold text-gray-600">🌐 Room language:</span>
      <span class="font-medium text-gray-800">{{ formatLocaleLabel(store.defaultLocale) }}</span>
    </div>

    <ul class="my-4 list-none p-0">
      <li
        v-for="player in store.playersList"
        :key="player.id"
        class="my-2 flex items-center justify-between gap-3 rounded bg-gray-50 p-3"
      >
        <div class="flex flex-1 items-center gap-2">
          <span class="font-medium">{{ player.name }}</span>
          <span v-if="player.id === store.localPlayerId" class="rounded bg-gray-200 px-2 py-1 text-sm text-gray-600">
            (You)
          </span>
          <span v-if="store.hostId === player.id" class="rounded bg-yellow-400 px-2 py-1 text-sm text-black">
            Host
          </span>
        </div>

        <div
          v-if="activeKickVotes.has(player.id)"
          class="flex items-center gap-2 rounded border border-yellow-400 bg-yellow-100 px-3 py-1.5"
        >
          <span class="text-sm font-semibold text-yellow-900">
            Kick vote:
            {{ activeKickVotes.get(player.id)?.currentVotes }}/{{ activeKickVotes.get(player.id)?.requiredVotes }}
          </span>
          <button
            v-if="player.id !== store.localPlayerId"
            type="button"
            class="cursor-pointer rounded bg-red-400 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-500"
            @click="voteToKick(player.id)"
          >
            Vote Kick
          </button>
        </div>

        <button
          v-else-if="canKickPlayer(player.id)"
          type="button"
          class="cursor-pointer rounded bg-danger px-3 py-1.5 text-sm font-semibold text-white hover:bg-danger-dark"
          @click="initiateKick(player.id)"
        >
          {{ store.isHost ? 'Kick' : 'Vote Kick' }}
        </button>
      </li>
    </ul>

    <div
      v-if="showKickConfirm"
      class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50"
      @click="cancelKick"
    >
      <div class="w-[90%] max-w-md rounded-md bg-white p-8 shadow-md" @click.stop>
        <h2 class="mb-4 text-xl font-bold text-ink">{{ store.isHost ? 'Kick Player?' : 'Start Kick Vote?' }}</h2>
        <p v-if="store.isHost" class="mb-6 text-gray-600">Are you sure you want to kick {{ targetPlayerName }}?</p>
        <p v-else class="mb-6 text-gray-600">
          Start a vote to kick {{ targetPlayerName }}?
          {{ targetIsHost
              ? 'All players must vote unanimously to kick the host.'
              : 'Requires 2/3 majority vote.' }}
        </p>
        <div class="flex justify-end gap-4">
          <button
            type="button"
            class="cursor-pointer rounded-md border-0 bg-success py-3.5 px-6 text-base font-semibold text-white transition-all hover:bg-success-dark"
            @click="cancelKick"
          >
            Cancel
          </button>
          <button
            v-if="showKickConfirm"
            type="button"
            class="cursor-pointer rounded-md bg-danger px-6 py-3 font-semibold text-white hover:bg-danger-dark"
            @click="confirmKick(showKickConfirm)"
          >
            {{ store.isHost ? 'Kick' : 'Start Vote' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
