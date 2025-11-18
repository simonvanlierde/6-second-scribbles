import { createRouter, createWebHistory } from 'vue-router'

import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

import Home from '../views/Home.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL || '/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
    },
    {
      // Redirect /room/:roomCode to /room/:roomCode/waiting
      path: '/room/:roomCode',
      redirect: (to) => ({
        name: 'waiting-room',
        params: { roomCode: to.params.roomCode },
      }),
    },
    {
      path: '/room/:roomCode/waiting',
      name: 'waiting-room',
      component: () => import('../views/room/WaitingRoomView.vue'),
    },
    {
      path: '/room/:roomCode/drawing',
      name: 'drawing',
      component: () => import('../views/room/DrawingView.vue'),
    },
    {
      // legacy alias used by some tests and external links
      path: '/room/:roomCode/draw',
      name: 'draw',
      component: () => import('../views/room/DrawingView.vue'),
    },
    {
      path: '/room/:roomCode/guessing',
      name: 'guessing',
      component: () => import('../views/room/GuessingView.vue'),
    },
    {
      path: '/room/:roomCode/scoring',
      name: 'scoring',
      component: () => import('../views/room/RoundResultsView.vue'),
    },
    {
      path: '/room/:roomCode/complete',
      name: 'complete',
      component: () => import('../views/room/FinalResultsView.vue'),
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('../views/PrivacyPolicy.vue'),
    },
    {
      path: '/credits',
      name: 'credits',
      component: () => import('../views/Credits.vue'),
    },
  ],
})

// Global guard: ensure store is hydrated for room routes and redirect to canonical phase route
router.beforeEach(async (to, from, next) => {
  // only apply to room routes
  const roomCode = to.params.roomCode as string | undefined
  if (!roomCode) return next()

  const store = useGameStore()
  const conn = useGameConnection()

  console.log('[Router Guard] Navigating to:', to.name, 'roomCode:', roomCode, 'current gamePhase:', store.gamePhase)

  // Connect if switching rooms or not connected
  if (store.roomCode !== roomCode && !conn.isConnected.value) {
    console.log('[Router Guard] Connecting to room:', roomCode)
    store.setRoomCode(roomCode)
    conn.connect(roomCode)
    // Ensure we have the latest server phase/state before routing
    try {
      console.log('[Router Guard] Requesting game state...')
      await conn.requestGameState()
      console.log('[Router Guard] Got game state, phase is now:', store.gamePhase)
    } catch (err) {
      console.warn('[Router Guard] Failed to get game state:', err)
      // ignore failures to hydrate state; we'll fall back to defaults
    }
  }


  // Redirect if we're not on the correct route for current phase
  if (to.name !== store.gamePhase) {
    console.log('[Router Guard] Redirecting from', to.name, 'to', store.gamePhase)
    return next({ name: store.gamePhase, params: { roomCode } })
  }

  console.log('[Router Guard] Allowing navigation to:', to.name)
  return next()
})

export default router
