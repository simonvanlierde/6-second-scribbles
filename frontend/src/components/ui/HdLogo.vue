<script setup lang="ts">
/* The app mark: a "6" drawn as one loose marker stroke on a wobbly card.
 * Same drawing as public/favicon.svg, but built from the card tokens so it
 * picks up the border, shadow and rotation the rest of the UI uses.
 * Size with --logo-size on the parent. */
</script>

<template>
  <span class="hd-logo">
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M21.5 5 C 13.5 7.5, 8.8 13, 8.8 19.5 C 8.8 25, 12.5 28, 17 27.4 C 21.4 26.8, 24 23.3, 22.4 20 C 20.9 16.6, 15.4 15.2, 11.6 18.2"
        stroke="var(--color-primary)"
        stroke-width="3.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </span>
</template>

<style scoped>
.hd-logo {
  display: inline-grid;
  place-items: center;
  width: var(--logo-size, 56px);
  height: var(--logo-size, 56px);
  background: var(--color-card);
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  rotate: var(--rotate-card);
}
.hd-logo svg {
  width: 82%;
  height: 82%;
}
</style>
