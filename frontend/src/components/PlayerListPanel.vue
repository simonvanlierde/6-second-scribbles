<script setup lang="ts">
import { computed, ref } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdPill from "@/components/ui/HdPill.vue";
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
    <ul class="player-list">
      <li v-for="player in store.playersList" :key="player.id" class="player-row">
        <div class="player-row__who">
          <HdAvatar
            :initial="getAvatarInitial(player.name)"
            :color="colorFor(player)"
            size="sm"
            :disconnected="!player.connected"
          />
          <span class="player-row__name" :class="{ 'player-row__name--away': !player.connected }">{{
            player.name
          }}</span>
          <HdPill v-if="!player.connected" class="player-row__muted">{{ $t("common.reconnecting") }}</HdPill>
          <HdPill v-if="player.id === store.localPlayerId">({{ $t("common.you") }})</HdPill>
          <HdPill v-if="store.hostId === player.id" variant="info">{{ $t("common.host") }}</HdPill>
          <HdPill v-if="activeKickVotes.has(player.id)">
            {{ $t("moderation.voteLabel") }}
            {{ activeKickVotes.get(player.id)?.currentVotes }}/{{ activeKickVotes.get(player.id)?.requiredVotes }}
          </HdPill>
        </div>

        <HdButton
          v-if="activeKickVotes.has(player.id) && player.id !== store.localPlayerId"
          variant="secondary"
          class="player-row__action"
          @click="voteToKick(player.id)"
        >
          {{ $t("moderation.voteKick") }}
        </HdButton>

        <HdButton v-else-if="canHostKick(player.id)" class="player-row__action" @click="openKickConfirm(player.id)">
          {{ $t("moderation.kickPlayer") }}
        </HdButton>

        <HdButton
          v-else-if="canVoteKick(player.id)"
          variant="secondary"
          class="player-row__action"
          @click="openKickConfirm(player.id)"
        >
          {{ $t("moderation.voteKick") }}
        </HdButton>
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

<style scoped>
.player-list {
  margin: var(--space-4) 0;
  padding: 0;
  list-style: none;
}
.player-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
  margin: var(--space-2) 0;
  padding: var(--space-2) var(--space-3);
  background: var(--color-card);
  color: var(--color-ink);
  border: var(--border-input) solid var(--color-ink);
  border-radius: var(--r-input);
}
.player-row__who {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.player-row__name {
  font-weight: 600;
}
.player-row__name--away,
.player-row .player-row__muted {
  color: var(--color-ink-muted);
}
.player-row .player-row__action {
  padding: 8px 14px;
  font-size: var(--text-label-md);
}
</style>
