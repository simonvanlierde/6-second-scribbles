import { defineStore } from "pinia";
import { ref } from "vue";

import { type UserResponse, UserResponseSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";
import { createLogger } from "@/shared/logger";

const log = createLogger("Auth");

export type AuthUser = UserResponse;

export const useAuthStore = defineStore("auth", () => {
  const currentUser = ref<AuthUser | null>(null);
  let bootstrapping = false;

  async function bootstrap(preferredLocale: string, displayName: string | null) {
    if (bootstrapping) return;
    bootstrapping = true;
    try {
      currentUser.value = await apiRequest("/api/me", {
        schema: UserResponseSchema,
      });
    } catch {
      try {
        currentUser.value = await apiRequest("/api/auth/guest", {
          method: "POST",
          body: { preferredLocale, displayName },
          schema: UserResponseSchema,
        });
      } catch (err) {
        log.warn("Guest sign-in failed:", err);
      }
    } finally {
      bootstrapping = false;
    }
  }

  return {
    currentUser,
    bootstrap,
  };
});
