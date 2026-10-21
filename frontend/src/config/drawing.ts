// Fixed pen palette — drawing colours must be theme-independent so the exported
// PNG looks the same for every viewer regardless of light/dark mode.
export const DRAW_PALETTE = ["#2d2d2d", "#ffffff", "#ff4d4d", "#2d5da1", "#2e9e5b", "#ff8c42"] as const;
// The drawing surface is always this light paper, in both themes, for the same
// reason. Keep in sync with --color-drawing-paper in styles/tokens.css.
export const DRAWING_PAPER = "#fdfbf7";
export const BRUSH_SIZES = [3, 6, 10] as const;

// i18n keys that name each pen colour and brush size for screen readers.
export const DRAW_COLOR_NAMES: Record<string, string> = {
  "#2d2d2d": "colors.black",
  "#ffffff": "colors.white",
  "#ff4d4d": "colors.red",
  "#2d5da1": "colors.blue",
  "#2e9e5b": "colors.green",
  "#ff8c42": "colors.orange",
};
export const BRUSH_SIZE_NAMES: Record<number, string> = {
  3: "drawing.brushSmall",
  6: "drawing.brushMedium",
  10: "drawing.brushLarge",
};
