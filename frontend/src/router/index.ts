import { createRouter, createWebHistory } from "vue-router";

import { normalizeRoomCode } from "@/shared/roomCode";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
    {
      path: "/rooms/:roomCode",
      name: "room",
      component: () => import("@/views/RoomView.vue"),
      beforeEnter: (to) => {
        const raw = String(to.params.roomCode || "");
        const code = normalizeRoomCode(raw);
        if (raw !== code) {
          return { name: "room", params: { roomCode: code } };
        }
        return true;
      },
    },
    {
      path: "/__ds",
      name: "design-system",
      component: () => import("@/views/DesignSystemView.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

export default router;
