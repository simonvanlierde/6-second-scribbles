<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import LocaleSelector from "@/components/LocaleSelector.vue";
import RoomCodeInput from "@/components/RoomCodeInput.vue";
import { showNotification } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { CreateRoomResponseSchema, RandomRoomResponseSchema, RoomStatusResponseSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game";

const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();
const { fetchLocaleAvailability, localeOptions } = useLocaleAvailability();

const playerName = computed({
  get: () => store.localPlayerName,
  set: (value: string) => {
    store.localPlayerName = value;
  },
});
const playerLocale = computed({
  get: () => store.localPlayerLocale,
  set: (value: string) => {
    store.setLocalPlayerLocale(value);
  },
});

const roomCodeModel = ref("");
const joinBtnRef = ref<HTMLButtonElement | null>(null);
const isJoiningRandom = ref(false);
const isCheckingRoom = ref(false);

onMounted(() => {
  void fetchLocaleAvailability();
});

watch(
  localeOptions,
  (options) => {
    const selected = options.find((option) => option.code === playerLocale.value);
    if (selected?.enabled) return;
    const fallback = options.find((option) => option.enabled);
    if (fallback) store.setLocalPlayerLocale(fallback.code);
  },
  { immediate: true },
);

function focusPlayerName() {
  const el = document.getElementById("player-name") as HTMLInputElement | null;
  if (el) el.focus();
}

function onRoomCodeComplete() {
  nextTick(() => {
    if (playerName.value.trim()) {
      if (!isCheckingRoom.value) void joinRoom();
    } else {
      if (joinBtnRef.value) joinBtnRef.value.focus();
    }
  });
}

function onRoomCodeSubmit() {
  if (playerName.value.trim()) {
    void joinRoom();
  } else {
    focusPlayerName();
  }
}

function onNameEnter() {
  if (roomCodeModel.value?.trim()) {
    void joinRoom();
  } else {
    void createRoom();
  }
}

async function createRoom() {
  if (!playerName.value.trim()) {
    showNotification("Please enter your name", "error");
    return;
  }

  try {
    const data = await apiRequest("/api/rooms", {
      method: "POST",
      schema: CreateRoomResponseSchema,
    });
    const roomCode = data.room_code;

    const playerId = getOrCreatePlayerId();
    store.setLocalPlayer(playerId, playerName.value.trim());
    store.setRoomCode(roomCode);

    connect(roomCode);
    router.push({ name: "room", params: { roomCode } });
  } catch (err) {
    console.error("Error creating room:", err);
    showNotification("Failed to create room. Please try again.", "error");
  }
}

async function joinRoom() {
  if (!playerName.value.trim()) {
    showNotification("Please enter your name", "error");
    return;
  }
  if (!roomCodeModel.value) {
    showNotification("Please enter a room code", "error");
    return;
  }

  const code = normalizeRoomCode(roomCodeModel.value);
  if (!isValidRoomCode(code)) {
    showNotification("Room code must be 6 characters (A–Z, 0–9)", "error");
    return;
  }

  isCheckingRoom.value = true;

  try {
    const data = await apiRequest(`/api/rooms/${code}/status`, {
      schema: RoomStatusResponseSchema,
    });
    if (!data.exists) {
      showNotification(`That room doesn't exist. Join a different room or create a new one!`, "error");
      return;
    }
  } catch {
    // Status check failed — proceed and let the WS connection handle it
  } finally {
    isCheckingRoom.value = false;
  }

  const playerId = getOrCreatePlayerId();
  store.setLocalPlayerAndSave(playerId, playerName.value.trim());
  store.setRoomCodeAndSave(code);

  connect(code);
  router.push({ name: "room", params: { roomCode: code } });
}

async function joinRandomRoom() {
  if (!playerName.value.trim()) {
    showNotification("Please enter your name", "error");
    return;
  }

  isJoiningRandom.value = true;

  try {
    const data = await apiRequest("/api/rooms/random", {
      schema: RandomRoomResponseSchema,
    });
    const roomCode = data.room_code;

    const playerId = getOrCreatePlayerId();
    store.setLocalPlayerAndSave(playerId, playerName.value.trim());
    store.setRoomCodeAndSave(roomCode);

    connect(roomCode);
    router.push({ name: "room", params: { roomCode } });
  } catch (err) {
    console.error("Error joining random room:", err);
    const message =
      err instanceof Error && err.message.includes("No available public rooms found")
        ? "No available rooms found. Try creating a new room!"
        : "Failed to connect. Please try again.";
    showNotification(message, "error");
  } finally {
    isJoiningRandom.value = false;
  }
}
</script>

<template>
  <div class="rounded-xl bg-white p-8 shadow-lg">
    <h2>{{ $t('home.createOrJoin') }}</h2>

    <div class="mb-6">
      <label for="player-name" class="mb-2 block font-semibold text-[#555]">{{ $t('home.yourName') }}</label>
      <input
        id="player-name"
        v-model="playerName"
        type="text"
        class="w-full rounded-md border-2 border-[#ddd] px-3 py-3 text-base transition-colors focus:border-primary focus:outline-none"
        :placeholder="$t('home.enterYourName')"
        maxlength="20"
        @keyup.enter="onNameEnter"
      >
    </div>

    <LocaleSelector id="player-locale" v-model="playerLocale" :options="localeOptions" label="Language" compact />

    <div class="flex flex-col gap-4">
      <button
        type="button"
        class="cursor-pointer rounded-md border-0 bg-gradient-to-br from-primary to-secondary px-6 py-3.5 text-base font-bold text-white transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-[0_6px_18px_rgba(102,126,234,0.45)]"
        @click="createRoom"
      >
        {{ $t('home.createRoom') }}
      </button>

      <div
        class="flex items-center gap-3 text-[0.8125rem] text-gray-400 before:h-px before:flex-1 before:bg-gray-200 before:content-[''] after:h-px after:flex-1 after:bg-gray-200 after:content-['']"
      >
        <span>{{ $t('home.orJoin') }}</span>
      </div>

      <div class="flex flex-col items-center">
        <RoomCodeInput v-model="roomCodeModel" @complete="onRoomCodeComplete" @submit="onRoomCodeSubmit" />
        <button
          ref="joinBtnRef"
          type="button"
          class="mt-3 w-full cursor-pointer rounded-md border-0 bg-success px-6 py-3.5 text-base font-semibold text-white transition-[background,transform] hover:-translate-y-px hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="isCheckingRoom"
          @click="joinRoom"
        >
          {{ isCheckingRoom ? $t('home.checking') : $t('home.joinRoom') }}
        </button>
      </div>

      <div
        class="flex items-center gap-3 text-[0.8125rem] text-gray-400 before:h-px before:flex-1 before:bg-gray-200 before:content-[''] after:h-px after:flex-1 after:bg-gray-200 after:content-['']"
      >
        <span>{{ $t('home.or') }}</span>
      </div>

      <button
        type="button"
        class="cursor-pointer rounded-md border-0 bg-primary px-6 py-3.5 text-base font-semibold text-white transition-[background,transform] hover:-translate-y-px hover:bg-primary-dark disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="isJoiningRandom"
        @click="joinRandomRoom"
      >
        {{ isJoiningRandom ? $t('home.findingRoom') : $t('home.joinRandomRoom') }}
      </button>
    </div>
  </div>
</template>
