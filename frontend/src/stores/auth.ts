import { defineStore } from "pinia";
import { ref } from "vue";

import { apiRequest } from "@/lib/api";

export type AuthUser = {
	id: string;
	username: string;
	displayName: string | null;
	preferredLocale: string;
	isGuest: boolean;
};

export const useAuthStore = defineStore("auth", () => {
	const currentUser = ref<AuthUser | null>(null);
	let bootstrapping = false;

	async function bootstrap(
		preferredLocale: string,
		displayName: string | null,
	) {
		if (bootstrapping) return;
		bootstrapping = true;
		try {
			currentUser.value = await apiRequest<AuthUser>("/api/me");
		} catch {
			currentUser.value = await apiRequest<AuthUser>("/api/auth/guest", {
				method: "POST",
				body: { preferredLocale, displayName },
			});
		} finally {
			bootstrapping = false;
		}
	}

	return { currentUser, bootstrap };
});
