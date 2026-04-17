<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";

import NamePromptDialog from "@/components/NamePromptDialog.vue";
import RoomCodeInput from "@/components/RoomCodeInput.vue";
import { showNotification } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { CreateRoomResponseSchema, RandomRoomResponseSchema, RoomStatusResponseSchema } from "@/generated/api";
import { i18n } from "@/i18n";
import { apiRequest } from "@/lib/api";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game";

const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();

const props = withDefaults(
  defineProps<{
    openNameEditorSignal?: number;
  }>(),
  {
    openNameEditorSignal: 0,
  },
);

const playerName = computed({
  get: () => store.localPlayerName,
  set: (value: string) => {
    store.localPlayerName = value;
  },
});

const roomCodeModel = ref("");
const joinBtnRef = ref<HTMLButtonElement | null>(null);
const isJoiningRandom = ref(false);
const isCheckingRoom = ref(false);
const nameDialogOpen = ref(false);
const nameDraft = ref("");
const pendingAction = ref<"create" | "join" | "random" | null>(null);
const nameDialogDescriptionKey = ref("roomEntry.needNameText");

watch(
  () => props.openNameEditorSignal,
  () => {
    if (!props.openNameEditorSignal) return;
    pendingAction.value = null;
    nameDialogDescriptionKey.value = "home.editNameHelp";
    focusPlayerName();
  },
);

function focusPlayerName() {
  nameDraft.value = playerName.value;
  nameDialogOpen.value = true;
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
    nameDialogDescriptionKey.value = "roomEntry.needNameText";
    focusPlayerName();
  }
}

async function createRoom() {
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
    showNotification(i18n.global.t("notifications.createRoomFailed"), "error");
  }
}

async function joinRoom() {
  if (!roomCodeModel.value) {
    showNotification(i18n.global.t("notifications.enterRoomCode"), "error");
    return;
  }

  const code = normalizeRoomCode(roomCodeModel.value);
  if (!isValidRoomCode(code)) {
    showNotification(i18n.global.t("notifications.invalidRoomCode"), "error");
    return;
  }

  isCheckingRoom.value = true;

  try {
    const data = await apiRequest(`/api/rooms/${code}/status`, {
      schema: RoomStatusResponseSchema,
    });
    if (!data.exists) {
      showNotification(i18n.global.t("notifications.roomDoesNotExist"), "error");
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
        ? i18n.global.t("notifications.noAvailableRooms")
        : i18n.global.t("notifications.connectFailed");
    showNotification(message, "error");
  } finally {
    isJoiningRandom.value = false;
  }
}

function ensurePlayerName(action: "create" | "join" | "random") {
  if (playerName.value.trim()) return false;
  pendingAction.value = action;
  nameDialogDescriptionKey.value = "roomEntry.needNameText";
  focusPlayerName();
  return true;
}

async function handleCreateRoom() {
  if (ensurePlayerName("create")) return;
  await createRoom();
}

async function handleJoinRoom() {
  if (ensurePlayerName("join")) return;
  await joinRoom();
}

async function handleJoinRandomRoom() {
  if (ensurePlayerName("random")) return;
  await joinRandomRoom();
}

async function handleNameConfirm() {
  if (!nameDraft.value.trim()) return;
  playerName.value = nameDraft.value.trim();
  const action = pendingAction.value;
  pendingAction.value = null;
  if (action === "create") await createRoom();
  if (action === "join") await joinRoom();
  if (action === "random") await joinRandomRoom();
}

function handleNameCancel() {
  pendingAction.value = null;
}
</script>

<template>
  <div
    class="overflow-hidden rounded-[28px] bg-white/96 p-4 shadow-[0_24px_60px_rgba(18,22,48,0.18)] backdrop-blur-sm md:p-6 lg:rounded-[32px] lg:px-7 lg:py-6"
  >
    <div class="mb-4 flex flex-col gap-3 md:mb-5 lg:gap-4">
      <p class="m-0 max-w-[44rem] text-[0.98rem] leading-relaxed text-slate-500 md:text-base">
        {{ $t('home.createOrJoinHelp') }}
      </p>
    </div>

    <div class="grid gap-3 md:gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-start xl:gap-5">
      <section
        class="flex min-w-0 self-start flex-col rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,rgba(102,126,234,0.12),rgba(255,255,255,0.72))] p-4 shadow-[0_14px_34px_rgba(15,23,42,0.05)] md:p-5 lg:pb-4"
      >
        <div class="space-y-1.5">
          <h3 class="m-0 text-[1.5rem] leading-tight font-bold text-slate-800">{{ $t('home.createRoom') }}</h3>
          <p class="m-0 text-sm leading-relaxed text-slate-500 md:text-[0.96rem]">{{ $t('home.createRoomHelp') }}</p>
        </div>
        <button
          type="button"
          class="mt-5 w-full cursor-pointer rounded-[20px] border-0 bg-gradient-to-br from-primary to-secondary px-6 py-3.5 text-base font-bold text-white transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-[0_16px_32px_rgba(102,126,234,0.28)] md:mt-6"
          @click="handleCreateRoom"
        >
          {{ $t('home.createRoom') }}
        </button>
      </section>

      <section
        class="flex min-w-0 flex-col rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.96),rgba(241,245,249,0.9))] p-4 shadow-[0_14px_34px_rgba(15,23,42,0.05)] md:p-5"
      >
        <div class="space-y-1.5">
          <h3 class="m-0 text-[1.5rem] leading-tight font-bold text-slate-800">{{ $t('home.joinRoom') }}</h3>
          <p class="m-0 text-sm leading-relaxed text-slate-500 md:text-[0.96rem]">{{ $t('home.joinWithCodeHelp') }}</p>
        </div>

        <div class="mt-4 flex min-w-0 flex-col items-center gap-3">
          <RoomCodeInput v-model="roomCodeModel" @complete="onRoomCodeComplete" @submit="onRoomCodeSubmit" />
          <button
            ref="joinBtnRef"
            type="button"
            class="w-full cursor-pointer rounded-[20px] border border-transparent bg-success px-6 py-3.5 text-base font-semibold text-white transition-[background,transform,box-shadow] hover:-translate-y-px hover:bg-success-dark hover:shadow-[0_12px_24px_rgba(72,187,120,0.22)] disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isCheckingRoom"
            @click="handleJoinRoom"
          >
            {{ isCheckingRoom ? $t('home.checking') : $t('home.joinRoom') }}
          </button>
        </div>

        <div class="mt-auto pt-4">
          <button
            type="button"
            class="w-full cursor-pointer rounded-[20px] border border-primary/18 bg-white/90 px-6 py-3.5 text-base font-semibold text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition-[background,transform,box-shadow] hover:-translate-y-px hover:bg-primary/6 hover:shadow-[0_8px_20px_rgba(102,126,234,0.12)] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="join-random-room-button"
            :disabled="isJoiningRandom"
            @click="handleJoinRandomRoom"
          >
            {{ isJoiningRandom ? $t('home.findingRoom') : $t('home.joinRandomRoom') }}
          </button>
        </div>
      </section>
    </div>

    <NamePromptDialog
      v-model:open="nameDialogOpen"
      v-model="nameDraft"
      :description-key="nameDialogDescriptionKey"
      @cancel="handleNameCancel"
      @confirm="handleNameConfirm"
    />
  </div>
</template>
