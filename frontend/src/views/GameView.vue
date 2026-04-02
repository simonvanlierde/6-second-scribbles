<script setup lang="ts">
import { computed } from "vue";

import DrawingPhase from "@/components/DrawingPhase.vue";
import GuessingPhase from "@/components/GuessingPhase.vue";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
// Computed binding ensures vue-tsc --build can infer the template context.
const gamePhase = computed(() => store.gamePhase);
</script>

<template>
  <DrawingPhase v-if="gamePhase === 'drawing'" />
  <GuessingPhase v-else-if="gamePhase === 'guessing'" />
  <div v-else class="waiting-screen">
    <div class="container">
      <h2>Waiting for round to start...</h2>
    </div>
  </div>
</template>

<style scoped>
.waiting-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}
</style>
