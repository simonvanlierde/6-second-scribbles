<script setup lang="ts">
import { computed, ref } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import HdTimer from "@/components/ui/HdTimer.vue";
import HdToast from "@/components/ui/HdToast.vue";
import { AVATAR_COLORS, getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { type ReactionKey, useReactions } from "@/composables/useReactions";
import { SOUND_KEYS, type SoundKey, useSound } from "@/composables/useSound";

const inputValue = ref("");
const codeValue = ref("A7KQ92");
const dialogOpen = ref(false);
const timerSeconds = ref(42);

const { enabled: soundEnabled, play } = useSound();
const reactions = useReactions();

const samplePlayers = ["simon", "maya", "jules", "anya", "rio", "kai"];
const playerSwatches = computed(() =>
  samplePlayers.map((name) => ({
    name,
    initial: getAvatarInitial(name),
    color: getAvatarColor(name),
  })),
);

const counts = computed(() => reactions.countsFor("demo"));

function onReact(k: ReactionKey): void {
  reactions.add("demo", k);
}

function playSound(k: SoundKey): void {
  play(k);
}

const soundKeys = Object.keys(SOUND_KEYS) as SoundKey[];

function setTheme(t: "light" | "dark" | null): void {
  const root = document.documentElement;
  if (t === null) root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", t);
}
</script>

<template>
  <div class="ds-page">
    <header class="ds-header">
      <h1>Design system · v1</h1>
      <div class="ds-header__actions">
        <HdButton variant="ghost" @click="setTheme('light')">Light</HdButton>
        <HdButton variant="ghost" @click="setTheme('dark')">Dark</HdButton>
        <HdButton variant="ghost" @click="setTheme(null)">System</HdButton>
      </div>
    </header>

    <section class="ds-section">
      <h2>Buttons</h2>
      <div class="ds-row">
        <HdButton variant="primary">Start a room</HdButton>
        <HdButton variant="secondary">Join with code</HdButton>
        <HdButton variant="success">Ready ✓</HdButton>
        <HdButton variant="ghost">change name</HdButton>
        <HdButton variant="primary" disabled>Disabled</HdButton>
      </div>
    </section>

    <section class="ds-section">
      <h2>Cards</h2>
      <div class="ds-row">
        <HdCard>
          <h3>Default card</h3>
          <p>Players: 4 / 10 — three are ready.</p>
        </HdCard>
        <HdCard variant="postit"> <strong>Tip · </strong> Press Enter to add another guess. </HdCard>
      </div>
    </section>

    <section class="ds-section">
      <h2>Inputs</h2>
      <div class="ds-row">
        <HdInput v-model="inputValue" placeholder="your name" aria-label="Your name" />
        <HdInput v-model="codeValue" variant="code" aria-label="Room code" />
      </div>
      <p>Value: {{ inputValue }} / {{ codeValue }}</p>
    </section>

    <section class="ds-section">
      <h2>Avatars</h2>
      <div class="ds-row">
        <HdAvatar
          v-for="(p, i) in playerSwatches"
          :key="p.name"
          :initial="p.initial"
          :color="p.color"
          :size="i % 3 === 0 ? 'sm' : i % 3 === 1 ? 'md' : 'lg'"
        />
      </div>
      <p>Palette tokens: {{ AVATAR_COLORS.join(', ') }}</p>
    </section>

    <section class="ds-section">
      <h2>Timer</h2>
      <div class="ds-row">
        <HdTimer :seconds="timerSeconds" />
        <HdButton variant="secondary" @click="timerSeconds = Math.max(0, timerSeconds - 5)"> -5 </HdButton>
        <HdButton variant="secondary" @click="timerSeconds = Math.min(99, timerSeconds + 5)"> +5 </HdButton>
        <HdPill variant="info">Drops to urgent at ≤ 10</HdPill>
      </div>
    </section>

    <section class="ds-section">
      <h2>Pills</h2>
      <div class="ds-row">
        <HdPill>default</HdPill>
        <HdPill variant="info">info</HdPill>
        <HdPill variant="success">ready ✓</HdPill>
      </div>
    </section>

    <section class="ds-section">
      <h2>Reactions</h2>
      <HdReactionPad @react="onReact" />
      <p>Counts: {{ counts }}</p>
    </section>

    <section class="ds-section">
      <h2>Dialog</h2>
      <HdButton variant="primary" @click="dialogOpen = true">Open dialog</HdButton>
      <HdDialog
        v-model:open="dialogOpen"
        title="Leave the room?"
        message="You'll lose your spot if the round has started."
        confirm-label="Leave"
        cancel-label="Stay"
        variant="danger"
      />
    </section>

    <section class="ds-section">
      <h2>Sound (off by default)</h2>
      <div class="ds-row">
        <HdPill :variant="soundEnabled ? 'success' : 'default'"> {{ soundEnabled ? 'on' : 'off' }} </HdPill>
        <HdButton variant="secondary" @click="soundEnabled = !soundEnabled"> Toggle </HdButton>
        <HdButton v-for="k in soundKeys" :key="k" variant="ghost" @click="playSound(k)"> {{ k }} </HdButton>
      </div>
      <p>No sound files ship in Sprint 0; clicks are no-ops if files 404.</p>
    </section>

    <HdToast />
  </div>
</template>

<style scoped>
.ds-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 96px;
  position: relative;
  z-index: 1;
}
.ds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px dashed var(--color-ink);
}
.ds-header__actions {
  display: flex;
  gap: 8px;
}
.ds-section {
  margin-bottom: 40px;
}
.ds-section h2 {
  margin: 0 0 16px;
}
.ds-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
