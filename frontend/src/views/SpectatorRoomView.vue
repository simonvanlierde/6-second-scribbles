<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { connect, disconnect } = useGameConnection();

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

function joinNextGame() {
  if (!store.roomCode || !store.localPlayerName.trim()) return;
  store.setSpectatorMode(false);
  store.setLocalPlayer(getOrCreatePlayerId(), store.localPlayerName.trim());
  connect(store.roomCode);
}

const drawings = computed(() => store.playersList.filter((player) => player.drawing));
const phaseLabel = computed(() => {
  if (store.gamePhase === "drawing") return "Drawing round";
  if (store.gamePhase === "guessing") return "Guessing round";
  if (store.gamePhase === "lobby") return "Room is back in the lobby";
  if (store.gamePhase === "round_results") return "Round results";
  if (store.gamePhase === "final_results") return "Final results";
  return "Watching room";
});
const canJoinNow = computed(() => store.gamePhase === "lobby" && store.localPlayerName.trim().length > 0);
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
        <p class="m-0 mb-2 text-xs tracking-widest text-white/70 uppercase">Room {{ store.roomCode }}</p>
        <h1 class="m-0">{{ phaseLabel }}</h1>
        <p class="m-0 mt-2 text-white/80">
          {{ canJoinNow
              ? 'The room is joinable again. Jump in for the next game whenever you are ready.'
              : 'Watching live updates. You can join when the room returns to the lobby.' }}
        </p>
      </div>
      <div class="flex flex-wrap justify-end gap-3">
        <button
          v-if="canJoinNow"
          type="button"
          class="cursor-pointer rounded-xl border-0 bg-gradient-to-br from-[#ffd166] to-[#ff8e72] px-4 py-3.5 font-extrabold text-[#1e1e1e]"
          @click="joinNextGame"
        >
          Join next game
        </button>
        <button
          type="button"
          class="leave-btn cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
          @click="leaveRoom"
        >
          Leave room
        </button>
      </div>
    </header>

    <section
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">Players</h2>
      <div class="mt-3 flex flex-wrap gap-2">
        <div
          v-for="player in store.playersList"
          :key="player.id"
          class="flex items-center gap-2 rounded-full bg-white/10 px-3 py-2"
        >
          {{ player.name }}
          <span class="text-sm text-white/70">{{ player.score }} pts</span>
        </div>
      </div>
    </section>

    <section
      v-if="store.gamePhase === 'drawing'"
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">Drawings</h2>
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
            :alt="`${player.name}'s drawing`"
            class="block h-[180px] w-full bg-black/15 object-contain"
          >
          <p class="p-3 text-white/85">{{ player.name }}</p>
        </article>
      </div>
      <p v-else class="p-3 text-white/85">No drawings have been published yet.</p>
    </section>

    <section
      v-else
      class="mx-auto w-full max-w-[1100px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] px-6 pt-5 pb-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <h2 class="m-0">Round status</h2>
      <p v-if="store.gamePhase === 'guessing'" class="p-3 text-white/85">
        Guessing is in progress. We'll move on once the round is complete.
      </p>
      <p v-else-if="store.gamePhase === 'lobby'" class="p-3 text-white/85">
        The room is waiting in the lobby again. Use “Join next game” to enter as a player.
      </p>
      <p v-else class="p-3 text-white/85">This room is between rounds. We'll keep you updated live.</p>
    </section>
  </div>
</template>
