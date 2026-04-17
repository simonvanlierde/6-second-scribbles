<script setup lang="ts">
import { computed, ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { formatLocaleLabel } from "@/shared/locales";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();

const showKickConfirm = ref<string | null>(null);

const activeKickVotes = computed(() => store.kickVotes);
const kickDialogOpen = computed({
  get: () => showKickConfirm.value !== null,
  set: (value: boolean) => {
    if (!value) {
      showKickConfirm.value = null;
    }
  },
});
const targetPlayer = computed(() => store.playersList.find((player) => player.id === showKickConfirm.value) ?? null);
const isHostKick = computed(() =>
  Boolean(store.isHost && targetPlayer.value && targetPlayer.value.id !== store.hostId),
);
const confirmTitle = computed(() => (isHostKick.value ? "Kick player?" : "Start vote-kick?"));
const confirmMessage = computed(() => {
  if (!targetPlayer.value) return "";
  if (isHostKick.value) {
    return `${targetPlayer.value.name} will be removed from the room immediately.`;
  }
  return `${targetPlayer.value.name} will stay in the room unless enough players vote to remove them.`;
});
const confirmLabel = computed(() => (isHostKick.value ? "Kick player" : "Start vote"));

function canHostKick(playerId: string): boolean {
  return store.isHost && playerId !== store.localPlayerId;
}

function canVoteKick(playerId: string): boolean {
  return !store.isHost && !store.isPrivateRoom && playerId !== store.localPlayerId && playerId !== store.hostId;
}

function openKickConfirm(targetPlayerId: string) {
  showKickConfirm.value = targetPlayerId;
}

function confirmKick() {
  if (!showKickConfirm.value) return;
  send({ type: "initiate_kick", targetPlayerId: showKickConfirm.value });
  showKickConfirm.value = null;
}

function cancelKick() {
  showKickConfirm.value = null;
}

function voteToKick(targetPlayerId: string) {
  send({ type: "cast_kick_vote", targetPlayerId });
}
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
          <span
            v-if="activeKickVotes.has(player.id)"
            class="rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-1 text-xs font-semibold text-yellow-900"
          >
            Vote:
            {{ activeKickVotes.get(player.id)?.currentVotes }}/{{ activeKickVotes.get(player.id)?.requiredVotes }}
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button
            v-if="activeKickVotes.has(player.id) && player.id !== store.localPlayerId"
            type="button"
            class="cursor-pointer rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-100"
            @click="voteToKick(player.id)"
          >
            Vote kick
          </button>

          <button
            v-else-if="canHostKick(player.id)"
            type="button"
            class="cursor-pointer rounded bg-danger px-3 py-1.5 text-sm font-semibold text-white hover:bg-danger-dark"
            @click="openKickConfirm(player.id)"
          >
            Kick
          </button>

          <button
            v-else-if="canVoteKick(player.id)"
            type="button"
            class="cursor-pointer rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:bg-slate-100"
            @click="openKickConfirm(player.id)"
          >
            Vote kick
          </button>
        </div>
      </li>
    </ul>

    <ConfirmDialog
      v-model:open="kickDialogOpen"
      :title="confirmTitle"
      :message="confirmMessage"
      :confirm-label="confirmLabel"
      cancel-label="Cancel"
      variant="danger"
      @confirm="confirmKick"
      @cancel="cancelKick"
    />
  </div>
</template>
