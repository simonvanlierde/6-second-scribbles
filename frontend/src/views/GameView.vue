<script setup lang="ts">
import { computed } from "vue";

import DrawingPhase from "@/components/DrawingPhase.vue";
import GuessingPhase from "@/components/GuessingPhase.vue";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const gamePhase = computed(() => store.gamePhase);
</script>

<template>
  <DrawingPhase v-if="gamePhase === 'drawing'" />
  <GuessingPhase v-else-if="gamePhase === 'guessing'" />
  <main v-else class="flex min-h-screen items-center justify-center">
    <div class="container">
      <h1>{{ $t('game.waitingForRound') }}</h1>
    </div>
  </main>
</template>
