// Apply the saved theme before first paint to avoid a flash of the wrong theme.
// Mirrors STORAGE_KEY/values in src/composables/useTheme.ts. Kept as a file
// rather than inline in index.html so the CSP can stay at script-src 'self'.
try {
  const t = localStorage.getItem("ds:theme");
  if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
} catch {
  // Storage blocked (private mode, disabled cookies): keep the default theme.
}
