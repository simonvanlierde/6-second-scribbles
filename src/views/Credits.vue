<script setup lang="ts">
import BackButton from '@/components/BackButton.vue'

const techs = [
  { name: 'Vue 3', url: 'https://vuejs.org/' },
  { name: 'TypeScript', url: 'https://www.typescriptlang.org/' },
  { name: 'PartyKit', url: 'https://partykit.dev/' },
  { name: 'Vite', url: 'https://vitejs.dev/' },
]
</script>

<template>
  <div class="credits-screen">
    <div class="credits-container">
      <div class="back-nav">
        <BackButton label="Back to Home" />
      </div>
      <div class="card credits-card">
        <h1>Credits</h1>
        <p class="intro-text">Thank you to everyone who inspired and supported this project.</p>

        <section class="credit-section">
          <h2>Original Game</h2>
          <p>
            <strong>Six Second Scribbles</strong> — physical card game created by Hazel Reynolds and
            published by
            <a
              href="https://gamelygames.com/products/six-second-scribbles"
              target="_blank"
              rel="noopener noreferrer"
              class="credit-link"
              >Gamely Games</a
            >.
          </p>
        </section>

        <section class="credit-section">
          <h2>Web Adaptation</h2>
          <p>
            This multiplayer version was inspired by
            <a
              href="https://github.com/OliverCulleyDeLange/6ss"
              target="_blank"
              rel="noopener noreferrer"
              class="credit-link"
              >Oliver Culley de Lange's single-player web version</a
            >.
          </p>
        </section>

        <section class="credit-section">
          <h2>Open Source</h2>
          <p>
            The source code for this multiplayer web adaptation is available on
            <a
              href="https://github.com/simonvanlierde/6-second-scribbles"
              target="_blank"
              rel="noopener noreferrer"
              class="credit-link github-link"
            >
              <svg
                class="github-icon"
                viewBox="0 0 16 16"
                width="16"
                height="16"
                fill="currentColor"
              >
                <path
                  d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
                ></path>
              </svg>
              GitHub
            </a>
            . Contributions, issues and suggestions are welcome.
          </p>
        </section>

        <section class="credit-section">
          <h2>Technologies</h2>
          <div class="tech-list">
            <template v-for="t in techs" :key="t.name">
              <a class="tech-tag" :href="t.url" target="_blank" rel="noopener noreferrer">
                {{ t.name }}
              </a>
            </template>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.credits-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.credits-container {
  max-width: 800px;
  width: 100%;
}

.back-nav {
  margin-bottom: 1.5rem;
}

.credits-card {
  background: white;
  border-radius: 20px;
  padding: 3rem;
  box-shadow:
    0 10px 40px rgba(0, 0, 0, 0.15),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin: 0 0 1rem 0;
  text-align: center;
  font-weight: 800;
}

.intro-text {
  color: #718096;
  text-align: center;
  font-size: 1.05rem;
  margin: 0 0 2.5rem 0;
  line-height: 1.6;
}

.credit-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #e2e8f0;
}

.credit-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.credit-section h2 {
  font-size: 1.5rem;
  color: #2d3748;
  margin: 0 0 1rem 0;
  font-weight: 700;
}

.credit-section p {
  color: #4a5568;
  font-size: 1.05rem;
  line-height: 1.7;
  margin: 0;
}

.credit-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.credit-link:hover {
  color: #5568d3;
  border-bottom-color: #5568d3;
}

.github-link {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.github-icon {
  display: inline-block;
  vertical-align: middle;
}

.tech-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}

.tech-tag {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.tech-tag {
  transition:
    transform 160ms ease,
    box-shadow 160ms ease;
  text-decoration: none; /* remove underline */
}
.tech-tag:hover,
.tech-tag:focus {
  transform: scale(1.06);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.25);
  outline: none;
}

@media (max-width: 768px) {
  .credits-card {
    padding: 2rem;
  }

  h1 {
    font-size: 2rem;
  }

  .credit-section h2 {
    font-size: 1.25rem;
  }

  .credit-section p {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .credits-screen {
    padding: 1rem 0.75rem;
  }

  .credits-card {
    padding: 1.5rem;
  }

  h1 {
    font-size: 1.75rem;
  }
}
</style>
