<script setup lang="ts">
import { useRouter, useRoute, RouterView } from 'vue-router'
import { onMounted, watch } from 'vue'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import logger from '@/utils/logger'
import ToastContainer from '@/components/ToastContainer.vue'
import IdlePrompt from '@/components/IdlePrompt.vue'
import IdleKickNotice from '@/components/IdleKickNotice.vue'
import AppFooter from '@/components/AppFooter.vue'

const router = useRouter()
const route = useRoute()
const store = useGameStore()
const { connect, isConnected, idlePromptMs, confirmIdle, idleKickedMessage, dismissIdleKick } =
  useGameConnection()

// Reconnect to room on page reload if we have saved state
onMounted(() => {
  if (store.roomCode && store.localPlayerId && !isConnected.value) {
    logger.info('Reconnecting to room:', store.roomCode)
    connect(store.roomCode)
  }
})

// Keep the URL in sync with the authoritative gamePhase
watch(
  () => store.gamePhase,
  (newPhase) => {
    const roomCode = route.params.roomCode as string | undefined
    if (!roomCode || !newPhase) return

    if (route.name !== newPhase) {
      logger.info('[App] Game phase changed to:', newPhase)
      // Use replace so we don't clutter history for server-driven transitions
      router.replace({ name: newPhase, params: { roomCode } }).catch(() => {})
    }
  }
)
</script>

<template>
  <div id="app">
    <main class="app-main">
      <RouterView />
    </main>
    <AppFooter />
    <ToastContainer />
    <IdlePrompt v-model="idlePromptMs" @confirm="confirmIdle" />
    <IdleKickNotice :message="idleKickedMessage" @dismiss="dismissIdleKick" />
  </div>
</template>

<style scoped>
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.app-main {
  flex: 1 1 auto; /* grow to fill available space so footer is pushed to bottom */
}
</style>
