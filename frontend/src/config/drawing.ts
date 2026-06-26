// Fixed pen palette — drawing colours must be theme-independent so the exported
// PNG looks the same for every viewer regardless of light/dark mode.
export const DRAW_PALETTE = ["#2d2d2d", "#ffffff", "#ff4d4d", "#2d5da1", "#2e9e5b", "#ff8c42"] as const;
export const BRUSH_SIZES = [3, 6, 10] as const;
