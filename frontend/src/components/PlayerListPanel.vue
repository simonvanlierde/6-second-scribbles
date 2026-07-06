<script setup lang="ts">
import { computed, ref } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection";
import { i18n } from "@/i18n";
import type { Player } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();

const showKickConfirm = ref<string | null>(null);

const activeKickVotes = computed(() => store.kickVotes);
const kickDialogOpen = computed({
  get: () => showKickConfirm.value !== null,
  set: () => {
    // Confirm/cancel handlers clear the target after HdDialog emits.
  },
});
const targetPlayer = computed(() => store.playersList.find((player) => player.id === showKickConfirm.value) ?? null);
const isHostKick = computed(() =>
  Boolean(store.isHost && targetPlayer.value && targetPlayer.value.id !== store.hostId),
);
const confirmTitle = computed(() =>
  i18n.global.t(isHostKick.value ? "moderation.kickPlayerTitle" : "moderation.startVoteKickTitle"),
);
const confirmMessage = computed(() => {
  if (!targetPlayer.value) return "";
  if (isHostKick.value) {
    return i18n.global.t("moderation.kickPlayerNow", { name: targetPlayer.value.name });
  }
  return i18n.global.t("moderation.voteKickNeedsVotes", { name: targetPlayer.value.name });
});
const confirmLabel = computed(() => i18n.global.t(isHostKick.value ? "moderation.kickPlayer" : "moderation.startVote"));

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

function colorFor(player: Player): string {
  // Prefer server-supplied colour; fall back to a deterministic per-id one.
  return player.color ?? getAvatarColor(player.id);
}
</script>

<template>
  <div>
    <ul class="my-4 list-none p-0">
      <li
        v-for="player in store.playersList"
        :key="player.id"
        class="my-2 flex items-center justify-between gap-3 rounded bg-gray-50 p-3"
      >
        <div class="flex flex-1 items-center gap-2">
          <HdAvatar
            :initial="getAvatarInitial(player.name)"
            :color="colorFor(player)"
            size="sm"
            :disconnected="!player.connected"
          />
          <span class="font-medium" :class="{ 'text-gray-400': !player.connected }">{{ player.name }}</span>
          <span
            v-if="!player.connected"
            class="rounded-full border border-gray-300 bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-500"
          >
            {{ $t("common.reconnecting") }}
          </span>
          <span v-if="player.id === store.localPlayerId" class="rounded bg-gray-200 px-2 py-1 text-sm text-gray-600">
            ({{ $t("common.you") }})
          </span>
          <span v-if="store.hostId === player.id" class="rounded bg-yellow-400 px-2 py-1 text-sm text-black">
            {{ $t("common.host") }}
          </span>
          <span
            v-if="activeKickVotes.has(player.id)"
            class="rounded-full border border-yellow-300 bg-yellow-100 px-2.5 py-1 text-xs font-semibold text-yellow-900"
          >
            {{ $t("moderation.voteLabel") }}
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
            {{ $t("moderation.voteKick") }}
          </button>

          <button
            v-else-if="canHostKick(player.id)"
            type="button"
            class="cursor-pointer rounded bg-danger px-3 py-1.5 text-sm font-semibold text-white hover:bg-danger-dark"
            @click="openKickConfirm(player.id)"
          >
            {{ $t("moderation.kickPlayer") }}
          </button>

          <button
            v-else-if="canVoteKick(player.id)"
            type="button"
            class="cursor-pointer rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:border-slate-400 hover:bg-slate-100"
            @click="openKickConfirm(player.id)"
          >
            {{ $t("moderation.voteKick") }}
          </button>
        </div>
      </li>
    </ul>

    <HdDialog
      v-model:open="kickDialogOpen"
      :title="confirmTitle"
      :message="confirmMessage"
      :confirm-label="confirmLabel"
      :cancel-label="$t('common.cancel')"
      variant="danger"
      @confirm="confirmKick"
      @cancel="cancelKick"
    />
  </div>
</template>
