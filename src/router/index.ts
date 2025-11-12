import { createRouter, createWebHistory } from 'vue-router'

import LobbyView from '../views/LobbyView.vue'

const router = createRouter({
  history: createWebHistory((import.meta as any).env?.BASE_URL || '/'),
  routes: [
    {
      path: '/',
      name: 'lobby',
      component: LobbyView,
    },
    {
      path: '/room/:roomCode',
      name: 'waiting-room',
      component: () => import('../views/WaitingRoomView.vue'),
    },
    {
      path: '/game/:roomCode',
      name: 'game',
      component: () => import('../views/GameView.vue'),
    },
    {
      path: '/round-results/:roomCode',
      name: 'round-results',
      component: () => import('../views/RoundResultsView.vue'),
    },
    {
      path: '/results/:roomCode',
      name: 'results',
      component: () => import('../views/ResultsView.vue'),
    },
  ],
})

export default router
