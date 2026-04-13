import { createRouter, createWebHistory } from "vue-router";

import { normalizeRoomCode } from "@/shared/roomCode";
import HomeView from "../views/HomeView.vue";
import RoomView from "../views/RoomView.vue";

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: "/",
			name: "home",
			component: HomeView,
		},
		{
			path: "/rooms/:roomCode",
			name: "room",
			component: RoomView,
			beforeEnter: (to, _from) => {
				const raw = String(to.params.roomCode || "");
				const code = normalizeRoomCode(raw);

				// Allow navigation for invalid codes so the UI can show a friendly message.
				// Only normalize the URL when the casing/format differs.
				if (raw !== code) {
					return { name: "room", params: { roomCode: code } };
				}

				return true;
			},
		},
		{
			path: "/:pathMatch(.*)*",
			redirect: "/",
		},
	],
});

export default router;
