<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdDialog from "@/components/ui/HdDialog.svelte";
import HdInput from "@/components/ui/HdInput.svelte";
import HdLogo from "@/components/ui/HdLogo.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import HdReactionPad from "@/components/ui/HdReactionPad.svelte";
import HdTimer from "@/components/ui/HdTimer.svelte";
import HdToast from "@/components/ui/HdToast.svelte";
import { AVATAR_COLORS, getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { type ReactionKey, useReactions } from "@/composables/useReactions.svelte";
import { SOUND_KEYS, type SoundKey, useSound } from "@/composables/useSound.svelte";

let inputValue = $state("");
let codeValue = $state("A7KQ92");
let dialogOpen = $state(false);
let timerSeconds = $state(42);

const sound = useSound();
const { play } = sound;
const reactions = useReactions();

const samplePlayers = ["simon", "maya", "jules", "anna", "rio", "kai"];
const playerSwatches = $derived(
  samplePlayers.map((name) => ({
    name,
    initial: getAvatarInitial(name),
    color: getAvatarColor(name),
  })),
);

const counts = $derived(reactions.countsFor("demo"));

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

  <div class="ds-page">
    <header class="ds-header">
      <h1>Design system · v1</h1>
      <div class="ds-header__actions">
        <span class="ds-header__label">Theme:</span>
        <HdButton variant="secondary" onclick={() => setTheme('light')}>Light</HdButton>
        <HdButton variant="secondary" onclick={() => setTheme('dark')}>Dark</HdButton>
        <HdButton variant="secondary" onclick={() => setTheme(null)}>Auto</HdButton>
      </div>
    </header>

    <section class="ds-section">
      <h2>Logo</h2>
      <div class="ds-row">
        <HdLogo style="--logo-size: 32px" />
        <HdLogo style="--logo-size: 48px" />
        <HdLogo style="--logo-size: 64px" />
      </div>
    </section>

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
        <HdInput bind:modelValue={inputValue} placeholder="your name" aria-label="Your name" />
        <HdInput bind:modelValue={codeValue} variant="code" aria-label="Room code" />
      </div>
      <p>Value: {inputValue} / {codeValue}</p>
    </section>

    <section class="ds-section">
      <h2>Avatars</h2>
      <div class="ds-row">
        {#each playerSwatches as p, i (p.name)}<HdAvatar
          initial={p.initial}
          color={p.color}
          size={i % 3 === 0 ? 'sm' : i % 3 === 1 ? 'md' : 'lg'}
        />{/each}
      </div>
      <p>Palette tokens: {AVATAR_COLORS.join(', ')}</p>
    </section>

    <section class="ds-section">
      <h2>Timer</h2>
      <div class="ds-row">
        <HdTimer seconds={timerSeconds} />
        <HdButton variant="secondary" onclick={() => { timerSeconds = Math.max(0, timerSeconds - 5); }}> -5 </HdButton>
        <HdButton variant="secondary" onclick={() => { timerSeconds = Math.min(99, timerSeconds + 5); }}> +5 </HdButton>
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
      <HdReactionPad name="Ada" onreact={onReact} />
      <p>Counts: {counts}</p>
    </section>

    <section class="ds-section">
      <h2>Dialog</h2>
      <HdButton variant="primary" onclick={() => { dialogOpen = true; }}>Open dialog</HdButton>
      <HdDialog
        bind:open={dialogOpen}
        title="Leave the room?"
        message="You'll lose your spot if the round has started."
        confirmLabel="Leave"
        cancelLabel="Stay"
        variant="danger"
      />
    </section>

    <section class="ds-section">
      <h2>Sound (off by default)</h2>
      <div class="ds-row">
        <HdPill variant={sound.enabled ? 'success' : 'default'}> {sound.enabled ? 'on' : 'off'} </HdPill>
        <HdButton variant="secondary" onclick={() => { sound.enabled = !sound.enabled; }}> Toggle </HdButton>
        {#each soundKeys as k (k)}<HdButton variant="ghost" onclick={() => playSound(k)}> {k} </HdButton>{/each}
      </div>
      <p>No sound files ship in Sprint 0; clicks are no-ops if files 404.</p>
    </section>

    <HdToast />
  </div>

<style>
:global(.ds-page) {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 96px;
  position: relative;
  z-index: 1;
}
:global(.ds-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px dashed var(--color-ink);
}
:global(.ds-header__actions) {
  display: flex;
  gap: 8px;
  align-items: center;
}
:global(.ds-header__label) {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
  margin-right: 4px;
}
:global(.ds-section) {
  margin-bottom: 40px;
}
:global(.ds-section) h2 {
  margin: 0 0 16px;
}
:global(.ds-row) {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
}
</style>
