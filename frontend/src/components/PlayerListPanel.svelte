<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdDialog from "@/components/ui/HdDialog.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();

let showKickConfirm = $state<string | null>(null);

let activeKickVotes = $derived.by(() => store.kickVotes);
let kickDialogOpen = $derived(showKickConfirm !== null);
let targetPlayer = $derived.by(() => store.playersList.find((player) => player.id === showKickConfirm) ?? null);
let isHostKick = $derived.by(() => Boolean(store.isHost && targetPlayer && targetPlayer.id !== store.hostId));
let confirmTitle = $derived.by(() => t(isHostKick ? "moderation.kickPlayerTitle" : "moderation.startVoteKickTitle"));
let confirmMessage = $derived.by(() => {
  if (!targetPlayer) return "";
  if (isHostKick) {
    return t("moderation.kickPlayerNow", { name: targetPlayer.name });
  }
  return t("moderation.voteKickNeedsVotes", { name: targetPlayer.name });
});
let confirmLabel = $derived.by(() => t(isHostKick ? "moderation.kickPlayer" : "moderation.startVote"));

function canHostKick(playerId: string): boolean {
  return store.isHost && playerId !== store.localPlayerId;
}

function canVoteKick(playerId: string): boolean {
  return !store.isHost && !store.isPrivateRoom && playerId !== store.localPlayerId && playerId !== store.hostId;
}

function openKickConfirm(targetPlayerId: string) {
  showKickConfirm = targetPlayerId;
}

function confirmKick() {
  if (!showKickConfirm) return;
  send({ type: "initiate_kick", targetPlayerId: showKickConfirm });
  showKickConfirm = null;
}

function cancelKick() {
  showKickConfirm = null;
}

function voteToKick(targetPlayerId: string) {
  send({ type: "cast_kick_vote", targetPlayerId });
}
</script>

<div>
  <ul class="player-list">
    {#each store.playersList as player (player.id)}
      <li class="player-row">
        <div class="player-row__who">
          <HdAvatar
            initial={getAvatarInitial(player.name)}
            color={player.color}
            size="sm"
            disconnected={!player.connected}
          ></HdAvatar>
          <span class={["player-row__name", { "player-row__name--away": !player.connected }]}>{player.name}</span>
          {#if !player.connected}
            <HdPill class="player-row__muted">{t("common.reconnecting")}</HdPill>
          {/if}
          {#if player.id === store.localPlayerId}
            <HdPill>({t("common.you")})</HdPill>
          {/if}
          {#if store.hostId === player.id}
            <HdPill variant="info">{t("common.host")}</HdPill>
          {/if}
          {#if activeKickVotes.has(player.id)}
            <HdPill>
              {t("moderation.voteLabel")}
              {activeKickVotes.get(player.id)?.currentVotes}/{activeKickVotes.get(player.id)?.requiredVotes}
            </HdPill>
          {/if}
        </div>

        {#if activeKickVotes.has(player.id) && player.id !== store.localPlayerId}
          <HdButton
            class="player-row__action"
            variant="secondary"
            onclick={() => {
              voteToKick(player.id);
            }}
          >
            {t("moderation.voteKick")}
          </HdButton>
        {:else if canHostKick(player.id)}
          <HdButton
            class="player-row__action"
            onclick={() => {
              openKickConfirm(player.id);
            }}
          >
            {t("moderation.kickPlayer")}
          </HdButton>
        {:else if canVoteKick(player.id)}
          <HdButton
            class="player-row__action"
            variant="secondary"
            onclick={() => {
              openKickConfirm(player.id);
            }}
          >
            {t("moderation.voteKick")}
          </HdButton>
        {/if}
      </li>
    {/each}
  </ul>

  <HdDialog
    open={kickDialogOpen}
    title={confirmTitle}
    message={confirmMessage}
    {confirmLabel}
    cancelLabel={t("common.cancel")}
    variant="danger"
    onconfirm={confirmKick}
    oncancel={cancelKick}
  ></HdDialog>
</div>

<style>
.player-list {
  margin: var(--space-4) 0;
  padding: 0;
  list-style: none;
}
.player-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
  margin: var(--space-2) 0;
  padding: var(--space-2) var(--space-3);
  background: var(--color-card);
  color: var(--color-ink);
  border: var(--border-input) solid var(--color-ink);
  border-radius: var(--r-input);
}
.player-row__who {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.player-row__name {
  font-weight: 600;
}
.player-row__name--away,
.player-row :global(span.hd-pill.player-row__muted) {
  color: var(--color-ink-muted);
}
.player-row :global(button.hd-btn.player-row__action) {
  min-height: 44px;
  padding: 8px 14px;
  font-size: var(--text-label-md);
}
</style>
