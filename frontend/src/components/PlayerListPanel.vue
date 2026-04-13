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

const targetPlayerName = computed(
	() => store.playersList.find((p) => p.id === showKickConfirm.value)?.name,
);
const targetIsHost = computed(
	() =>
		store.playersList.find((p) => p.id === showKickConfirm.value)?.id ===
		store.hostId,
);
</script>

<template>
  <div>
    <!-- Room language indicator for non-host players -->
    <div v-if="!store.isHost" class="language-indicator">
      <span class="language-label">🌐 Room language:</span>
      <span class="language-value">{{ formatLocaleLabel(store.defaultLocale) }}</span>
    </div>

    <ul class="player-list">
      <li v-for="player in store.playersList" :key="player.id" class="player-item">
        <div class="player-info">
          <span class="player-name">{{ player.name }}</span>
          <span v-if="player.id === store.localPlayerId" class="player-badge">(You)</span>
          <span v-if="store.hostId === player.id" class="player-badge host">Host</span>
        </div>

        <!-- Active kick vote status -->
        <div v-if="activeKickVotes.has(player.id)" class="kick-vote-status">
          <span class="vote-progress">
            Kick vote:
            {{ activeKickVotes.get(player.id)?.currentVotes }}/{{ activeKickVotes.get(player.id)?.requiredVotes }}
          </span>
          <button
            v-if="player.id !== store.localPlayerId"
            type="button"
            class="btn btn-small btn-vote"
            @click="voteToKick(player.id)"
          >
            Vote Kick
          </button>
        </div>

        <!-- Kick / Vote Kick button -->
        <button
          v-else-if="canKickPlayer(player.id)"
          type="button"
          class="btn btn-small btn-kick"
          @click="initiateKick(player.id)"
        >
          {{ store.isHost ? 'Kick' : 'Vote Kick' }}
        </button>
      </li>
    </ul>

    <!-- Kick confirmation modal -->
    <div v-if="showKickConfirm" class="modal-overlay" @click="cancelKick">
      <div class="modal-content" @click.stop>
        <h2>{{ store.isHost ? 'Kick Player?' : 'Start Kick Vote?' }}</h2>
        <p v-if="store.isHost">Are you sure you want to kick {{ targetPlayerName }}?</p>
        <p v-else>
          Start a vote to kick {{ targetPlayerName }}?
          {{ targetIsHost ? 'All players must vote unanimously to kick the host.' : 'Requires 2/3 majority vote.' }}
        </p>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="cancelKick">Cancel</button>
          <button v-if="showKickConfirm" type="button" class="btn btn-danger" @click="confirmKick(showKickConfirm)">
            {{ store.isHost ? 'Kick' : 'Start Vote' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.player-item {
  padding: 0.75rem;
  margin: 0.5rem 0;
  background-color: #f8f9fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.player-name {
  font-weight: 500;
}

.player-badge {
  padding: 0.25rem 0.5rem;
  background-color: #e9ecef;
  border-radius: 3px;
  font-size: 0.875rem;
  color: #6c757d;
}

.player-badge.host {
  background-color: #ffc107;
  color: #000;
}

.player-badge.locale {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.btn-kick {
  background-color: var(--color-danger);
  color: white;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.btn-kick:hover {
  background-color: #c82333;
}

.btn-vote {
  background-color: #ff6b6b;
  color: white;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.btn-vote:hover {
  background-color: #ff5252;
}

.kick-vote-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: #fff3cd;
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  border: 1px solid #ffc107;
}

.vote-progress {
  font-size: 0.875rem;
  font-weight: 600;
  color: #856404;
}

.language-indicator {
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
}

.language-label {
  font-weight: 600;
  color: #495057;
}

.language-value {
  color: #212529;
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: var(--radius-md);
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-text);
}

.modal-content p {
  margin-bottom: 1.5rem;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}
</style>
