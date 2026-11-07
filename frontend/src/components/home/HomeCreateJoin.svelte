<script lang="ts">
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdInput from "@/components/ui/HdInput.svelte";
import { showNotification } from "@/composables/notifications.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useSettingsPanel } from "@/composables/useSettingsPanel.svelte";
import { CreateRoomResponseSchema, QuickPlayResponseSchema, RoomStatusResponseSchema } from "@/generated/api";
import { t } from "@/i18n";
import { ApiError, apiRequest } from "@/lib/api";
import { useRouter } from "@/router";
import { generateRandomName } from "@/shared/nameGenerator";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game.svelte";

const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();
const { openForName } = useSettingsPanel();

let roomCodeModel = $state("");
let isCheckingRoom = $state(false);
let isQuickPlaying = $state(false);

function ensurePlayerName(resume: () => void): boolean {
  if (store.localPlayerName.trim()) return true;
  // Open the name prompt and resume this action once a name is set, so the
  // player's click isn't lost to the detour through Settings.
  openForName(resume);
  return false;
}

// 429 means the network's room cap or the creation rate limit; an immediate retry fails too.
function roomCreationError(err: unknown, fallbackKey: string): string {
  return t(err instanceof ApiError && err.status === 429 ? "notifications.tooManyRooms" : fallbackKey);
}

async function navigateToRoom(roomCode: string) {
  const playerId = getOrCreatePlayerId();
  store.setLocalPlayer(playerId, store.localPlayerName.trim());
  store.setRoomCode(roomCode);
  connect(roomCode);
  await router.push({ name: "room", params: { roomCode } });
}

async function handleCreateRoom() {
  if (!ensurePlayerName(handleCreateRoom)) return;
  try {
    // Trailing slash: the backend route is "/" under /rooms, so "/api/rooms" costs a 307 redirect.
    const data = await apiRequest("/api/rooms/", {
      method: "POST",
      schema: CreateRoomResponseSchema,
    });
    await navigateToRoom(data.room_code);
  } catch (err) {
    showNotification(roomCreationError(err, "notifications.createRoomFailed"), "error");
  }
}

async function handleJoinRoom() {
  if (!ensurePlayerName(handleJoinRoom)) return;
  if (!roomCodeModel) {
    showNotification(t("notifications.enterRoomCode"), "error");
    return;
  }

  const code = normalizeRoomCode(roomCodeModel);
  if (!isValidRoomCode(code)) {
    showNotification(t("notifications.invalidRoomCode"), "error");
    return;
  }

  isCheckingRoom = true;
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
    isCheckingRoom = false;
  }

  await navigateToRoom(code);
}

async function handleQuickPlay() {
  if (!store.localPlayerName.trim()) {
    store.localPlayerName = generateRandomName();
  }
  isQuickPlaying = true;
  try {
    const data = await apiRequest("/api/rooms/quick-play", {
      method: "POST",
      schema: QuickPlayResponseSchema,
    });
    await navigateToRoom(data.room_code);
  } catch (err) {
    showNotification(roomCreationError(err, "notifications.connectFailed"), "error");
  } finally {
    isQuickPlaying = false;
  }
}
</script>

<HdCard class="home-cta">
  <div class="home-cta__primary">
    <HdButton variant="primary" onclick={handleCreateRoom}> {t("home.createRoom")} </HdButton>
  </div>

  <div class="home-cta__join">
    <HdInput
      bind:modelValue={roomCodeModel}
      variant="code"
      ariaLabel={t("home.roomCodeLabel")}
      placeholder={t("home.roomCodeLabel")}
      maxlength={6}
      onkeydown={(event) => {
        if (event.key === "Enter") void handleJoinRoom();
      }}
    ></HdInput>
    <HdButton variant="success" disabled={isCheckingRoom} onclick={handleJoinRoom}>
      {isCheckingRoom ? t("home.checking") : t("home.joinRoom")}
    </HdButton>
  </div>

  <HdCard class="home-cta__quick" variant="postit">
    <div class="home-cta__quick-text">
      <strong>{t("home.quickPlayHeading")}</strong>
      <span>{t("home.quickPlayBody")}</span>
    </div>
    <HdButton variant="secondary" disabled={isQuickPlaying} onclick={handleQuickPlay}>
      {t("home.quickPlayCta")}
    </HdButton>
  </HdCard>
</HdCard>

<style>
:global(div.hd-card.home-cta) {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.home-cta__primary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.home-cta__primary > :global(*) {
  flex: 1;
  min-width: 160px;
}
.home-cta__join {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
:global(div.hd-card.home-cta__quick) {
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
