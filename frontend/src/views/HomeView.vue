<script setup lang="ts">
import CreateJoinCard from "@/components/CreateJoinCard.vue";
import HowToPlay from "@/components/HowToPlay.vue";
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-5">
    <div class="max-w-[1200px] w-full">
      <h1>🎨 {{ $t('home.title') }}</h1>
      <p class="mb-8 text-center text-[1.2rem] text-white/90">{{ $t('home.subtitle') }}</p>

      <div class="flex flex-col gap-4">
        <CreateJoinCard />
        <HowToPlay />
      </div>

      <footer
        class="mt-6 pb-4 text-center text-[0.78rem] leading-relaxed text-white/65 [&_a]:text-white/85 [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-white"
      >
        <p>
          A multiplayer web version of
          <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener">
            Six Second Scribbles
          </a>
          by Gamely Games · Inspired by
          <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener">
            Oliver Culley de Lange's solo version
          </a>
          ·
          <a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener">
            Source on GitHub
          </a>
        </p>
      </footer>
    </div>
  </div>
</template>
