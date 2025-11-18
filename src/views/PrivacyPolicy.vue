<script setup lang="ts">
import BackButton from '@/components/BackButton.vue'
</script>

<template>
  <div class="privacy-screen">
    <div class="privacy-container">
      <div class="back-nav">
        <BackButton label="Back to Home" />
      </div>
      <div class="card privacy-card">
        <h1>Privacy Policy</h1>
        <p class="last-updated">Last updated: November 15, 2025</p>

        <section class="policy-section">
          <h2>What data we collect</h2>
          <div class="info-list">
            <div class="info-item">
              <h3>Display name</h3>
              <p>
                Saved locally and sent to other players when you join a room so people can see who
                you are.
              </p>
            </div>
            <div class="info-item">
              <h3>Room codes & game messages</h3>
              <p>
                Used to connect players and run the game. Drawings and guesses are relayed in real
                time.
              </p>
            </div>
          </div>
        </section>

        <section class="policy-section">
          <h2>How we use it</h2>
          <p class="simple-text">
            Only to make the game work — to connect players and run matches. We do not sell your
            data or use it for advertising.
          </p>
        </section>

        <section class="policy-section">
          <h2>Your choices</h2>
          <ul class="control-list">
            <li>Use any display name you like (pseudonyms are fine)</li>
            <li>Clear your browser storage to remove local data</li>
            <li>Contact us via GitHub issues if you need help or want data removed</li>
          </ul>
        </section>

        <section class="policy-section last-section">
          <h2>Questions?</h2>
          <p class="simple-text">
            Open an issue on GitHub if you have privacy questions:
            <a
              href="https://github.com/simonvanlierde/6-second-scribbles/issues"
              target="_blank"
              rel="noopener noreferrer"
              class="policy-link"
              >Project issues</a
            >
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.privacy-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.privacy-container {
  max-width: 900px;
  width: 100%;
}

.back-nav {
  margin-bottom: 1.5rem;
}

.privacy-card {
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
  margin: 0 0 0.5rem 0;
  text-align: center;
  font-weight: 800;
}

.last-updated {
  color: #a0aec0;
  text-align: center;
  font-size: 0.9rem;
  margin: 0 0 2rem 0;
  font-style: italic;
}

.intro {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  padding: 1.5rem;
  border-radius: 12px;
  margin-bottom: 2.5rem;
  border-left: 4px solid #667eea;
}

.intro p {
  color: #4a5568;
  font-size: 1.1rem;
  line-height: 1.7;
  margin: 0;
  font-weight: 500;
}

.policy-section {
  margin-bottom: 2.5rem;
}

.last-section {
  margin-bottom: 0;
}

.policy-section h2 {
  font-size: 1.5rem;
  color: #2d3748;
  margin: 0 0 1rem 0;
  font-weight: 700;
}

.simple-text {
  color: #4a5568;
  font-size: 1.05rem;
  line-height: 1.7;
  margin: 0;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.info-item {
  background: #f8fafc;
  padding: 1.25rem;
  border-radius: 12px;
  border-left: 3px solid #667eea;
}

.info-item h3 {
  font-size: 1.1rem;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
  font-weight: 700;
}

.info-item p {
  color: #4a5568;
  font-size: 1rem;
  line-height: 1.6;
  margin: 0;
}

.control-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.control-list li {
  color: #4a5568;
  font-size: 1.05rem;
  line-height: 1.6;
  padding-left: 1.75rem;
  position: relative;
}

.control-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #667eea;
  font-weight: bold;
  font-size: 1.2rem;
}

.policy-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.policy-link:hover {
  color: #5568d3;
  border-bottom-color: #5568d3;
}

@media (max-width: 768px) {
  .privacy-card {
    padding: 2rem;
  }

  h1 {
    font-size: 2rem;
  }

  .policy-section h2 {
    font-size: 1.25rem;
  }

  .simple-text,
  .control-list li {
    font-size: 1rem;
  }

  .intro p {
    font-size: 1.05rem;
  }
}

@media (max-width: 480px) {
  .privacy-screen {
    padding: 1rem 0.75rem;
  }

  .privacy-card {
    padding: 1.5rem;
  }

  h1 {
    font-size: 1.75rem;
  }

  .policy-section h2 {
    font-size: 1.15rem;
  }

  .intro {
    padding: 1rem;
  }

  .info-item {
    padding: 1rem;
  }
}
</style>
