<script setup lang="ts">
import { computed } from "vue";

import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { leaveRoom } = useLeaveRoom();

const drawings = computed(() => store.playersList.filter((player) => player.drawing));
const phaseLabel = computed(() => (store.gamePhase === "drawing" ? "Drawing round" : "Guessing round"));
</script>

<template>
  <div class="spectator-screen">
    <header class="spectator-header">
      <div>
        <p class="eyebrow">Room {{ store.roomCode }}</p>
        <h1>{{ phaseLabel }}</h1>
        <p class="subcopy">Watching live updates. You can join when the room returns to the lobby.</p>
      </div>
      <button type="button" class="leave-btn" @click="leaveRoom">Leave room</button>
    </header>

    <section class="panel">
      <h2>Players</h2>
      <div class="player-list">
        <div v-for="player in store.playersList" :key="player.id" class="player-chip">
          {{ player.name }}
          <span class="score">{{ player.score }} pts</span>
        </div>
      </div>
    </section>

    <section v-if="store.gamePhase === 'drawing'" class="panel">
      <h2>Drawings</h2>
      <div v-if="drawings.length" class="drawing-grid">
        <article v-for="player in drawings" :key="player.id" class="drawing-card">
          <img :src="player.drawing" :alt="`${player.name}'s drawing`" class="drawing-image">
          <p>{{ player.name }}</p>
        </article>
      </div>
      <p v-else class="empty-state">No drawings have been published yet.</p>
    </section>

    <section v-else class="panel">
      <h2>Round status</h2>
      <p class="empty-state">Guessing is in progress. We’ll move on once the round is complete.</p>
    </section>
  </div>
</template>

<style scoped>
.spectator-screen {
  min-height: 100vh;
  padding: 1.5rem;
  display: grid;
  gap: 1rem;
  background: var(--color-bg-gradient);
  color: white;
}

.spectator-header,
.panel {
  width: min(1100px, 100%);
  margin: 0 auto;
  border-radius: 24px;
  background: rgba(10, 12, 28, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(14px);
}

.spectator-header {
  padding: 1.5rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.panel {
  padding: 1.25rem 1.5rem 1.5rem;
}

.eyebrow {
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.72);
}

h1,
h2,
p {
  margin: 0;
}

.subcopy {
  margin-top: 0.5rem;
  color: rgba(255, 255, 255, 0.82);
}

.leave-btn {
  border: 0;
  border-radius: 14px;
  padding: 0.85rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-weight: 800;
  cursor: pointer;
}

.player-list {
  margin-top: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.player-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
}

.score {
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.875rem;
}

.drawing-grid {
  margin-top: 0.75rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

.drawing-card {
  border-radius: 18px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.drawing-image {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: contain;
  background: rgba(0, 0, 0, 0.16);
}

.drawing-card p,
.empty-state {
  padding: 0.75rem;
  color: rgba(255, 255, 255, 0.86);
}
</style>
