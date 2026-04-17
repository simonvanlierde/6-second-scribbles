import { defineStore } from "pinia";
import { readonly, ref } from "vue";

import { type UserResponse, UserResponseSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";

export type AuthUser = UserResponse;

export const useAuthStore = defineStore("auth", () => {
  const currentUser = ref<AuthUser | null>(null);
  const isBootstrapping = ref(false);
  const bootstrapError = ref<string | null>(null);

  async function bootstrap(preferredLocale: string, displayName: string | null) {
    if (isBootstrapping.value) return;
    isBootstrapping.value = true;
    bootstrapError.value = null;
    try {
      currentUser.value = await apiRequest("/api/me", { schema: UserResponseSchema });
    } catch {
      try {
        currentUser.value = await apiRequest("/api/auth/guest", {
          method: "POST",
          body: { preferredLocale, displayName },
          schema: UserResponseSchema,
        });
      } catch (err) {
        bootstrapError.value = err instanceof Error ? err.message : "Failed to authenticate";
      }
    } finally {
      isBootstrapping.value = false;
    }
  }

  return {
    currentUser,
    isBootstrapping: readonly(isBootstrapping),
    bootstrapError: readonly(bootstrapError),
    bootstrap,
  };
});
