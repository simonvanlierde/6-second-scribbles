<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdInput from "@/components/ui/HdInput.vue";
import { showNotification } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { useSettingsPanel } from "@/composables/useSettingsPanel";
import { CreateRoomResponseSchema, QuickPlayResponseSchema, RoomStatusResponseSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";
import { generateRandomName } from "@/shared/nameGenerator";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game";

const { t } = useI18n({ useScope: "global" });
const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();
const { openForName } = useSettingsPanel();

const roomCodeModel = ref("");
const isCheckingRoom = ref(false);
const isQuickPlaying = ref(false);

function ensurePlayerName(): boolean {
  if (store.localPlayerName.trim()) return true;
  openForName();
  return false;
}

async function navigateToRoom(roomCode: string) {
  const playerId = getOrCreatePlayerId();
  store.setLocalPlayer(playerId, store.localPlayerName.trim());
  store.setRoomCode(roomCode);
  connect(roomCode);
  await router.push({ name: "room", params: { roomCode } });
}

async function handleCreateRoom() {
  if (!ensurePlayerName()) return;
  try {
    const data = await apiRequest("/api/rooms", {
      method: "POST",
      schema: CreateRoomResponseSchema,
    });
    await navigateToRoom(data.room_code);
  } catch {
    showNotification(t("notifications.createRoomFailed"), "error");
  }
}

async function handleJoinRoom() {
  if (!ensurePlayerName()) return;
  if (!roomCodeModel.value) {
    showNotification(t("notifications.enterRoomCode"), "error");
    return;
  }

  const code = normalizeRoomCode(roomCodeModel.value);
  if (!isValidRoomCode(code)) {
    showNotification(t("notifications.invalidRoomCode"), "error");
    return;
  }

  isCheckingRoom.value = true;
  try {
    const data = await apiRequest(`/api/rooms/${code}/status`, {
      schema: RoomStatusResponseSchema,
    });
    if (!data.exists) {
      showNotification(t("notifications.roomDoesNotExist"), "error");
      return;
    }
  } catch {
    // Fall through — let the WS connection surface a clearer error.
  } finally {
    isCheckingRoom.value = false;
  }

  await navigateToRoom(code);
}

async function handleQuickPlay() {
  if (!store.localPlayerName.trim()) {
    store.localPlayerName = generateRandomName();
  }
  isQuickPlaying.value = true;
  try {
    const data = await apiRequest("/api/rooms/quick-play", {
      method: "POST",
      schema: QuickPlayResponseSchema,
    });
    await navigateToRoom(data.room_code);
  } catch {
    showNotification(t("notifications.connectFailed"), "error");
  } finally {
    isQuickPlaying.value = false;
  }
}
</script>

<template>
  <HdCard class="home-cta">
    <div class="home-cta__primary">
      <HdButton variant="primary" @click="handleCreateRoom"> {{ t("home.createRoom") }} </HdButton>
    </div>

    <div class="home-cta__join">
      <HdInput
        v-model="roomCodeModel"
        variant="code"
        :aria-label="t('home.roomCodeLabel')"
        :placeholder="t('home.roomCodeLabel')"
        maxlength="6"
        @keydown.enter="handleJoinRoom"
      />
      <HdButton variant="success" :disabled="isCheckingRoom" @click="handleJoinRoom">
        {{ isCheckingRoom ? t("home.checking") : t("home.joinRoom") }}
      </HdButton>
    </div>

    <HdCard variant="postit" class="home-cta__quick">
      <div class="home-cta__quick-text">
        <strong>{{ t("home.quickPlayHeading") }}</strong>
        <span>{{ t("home.quickPlayBody") }}</span>
      </div>
      <HdButton variant="secondary" :disabled="isQuickPlaying" @click="handleQuickPlay">
        {{ t("home.quickPlayCta") }}
      </HdButton>
    </HdCard>
  </HdCard>
</template>

<style scoped>
.home-cta {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.home-cta__primary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.home-cta__primary > * {
  flex: 1;
  min-width: 160px;
}
.home-cta__join {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.home-cta__quick {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.home-cta__quick-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.95rem;
}
.home-cta__quick-text strong {
  font-family: var(--font-display);
  font-size: 1.05rem;
}
</style>
