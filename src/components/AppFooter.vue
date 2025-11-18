<template>
  <footer class="app-footer">
    <div class="footer-links">
      <a
        class="icon-link"
        :href="githubUrl"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Open source repository on GitHub"
      >
        <font-awesome-icon icon="fa-brands fa-github" />
        <span class="sr-only">Open GitHub (new tab)</span>
      </a>

      <RouterLink class="text-link footer-link-scale" to="/privacy">Privacy Policy</RouterLink>
      <RouterLink class="text-link footer-link-scale" to="/credits">Credits</RouterLink>
    </div>

    <!-- Attribution moved to the Lobby page; footer kept compact with links only -->
  </footer>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

// using font-awesome brand icon for GitHub
// If you want to parametrize the GitHub URL from config later, do that here.
const githubUrl = 'https://github.com/simonvanlierde/6-second-scribbles'
</script>

<style scoped>
.app-footer {
  display: flex;
  justify-content: center; /* center the small link set */
  align-items: center;
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: var(--footer-bg, #2c3e50); /* match drawing header */
  color: #f6f8fa;
  border-top: 1px solid rgba(0, 0, 0, 0.12);
  font-size: 0.9rem;
  box-shadow: 0 -1px 0 rgba(0, 0, 0, 0.05);
  width: 100%;
  box-sizing: border-box;
}
.footer-links {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  max-width: 980px;
  margin: 0 auto;
  overflow: hidden;
  flex-wrap: wrap;
  justify-content: center;
}
.footer-links a {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.icon-link svg {
  display: inline-block;
  vertical-align: middle;
  width: 20px;
  height: 20px;
  fill: currentColor;
}
.text-link {
  color: var(--footer-link, #9fb7d9);
  text-decoration: none;
}
.text-link.router-link-active {
  color: #ffffff;
  text-decoration: underline;
}
.icon-link {
  color: #f6f8fa;
}

/* accessible hidden text */
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

.icon-link:hover,
.icon-link:focus {
  transform: scale(1.08);
  color: #cfe7ff;
}

.icon-link {
  transition:
    transform 140ms ease,
    color 140ms ease;
}

.footer-link-scale {
  transition:
    transform 140ms ease,
    color 140ms ease;
}

.footer-link-scale:hover,
.footer-link-scale:focus {
  transform: scale(1.06);
  color: #cfe7ff;
}
</style>
