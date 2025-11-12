<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import ToastContainer from '@/components/ToastContainer.vue'

const store = useGameStore()
const { connect, isConnected } = useGameConnection()

// Reconnect to room on page reload if we have saved state
onMounted(() => {
  if (store.roomCode && store.localPlayerId && !isConnected.value) {
    console.log('Reconnecting to room:', store.roomCode)
    connect(store.roomCode)
  }
})
</script>

<template>
  <div id="app">
    <RouterView />
    <ToastContainer />
  </div>
</template>

<style scoped>
#app {
  width: 100%;
  min-height: 100vh;
}
</style>
