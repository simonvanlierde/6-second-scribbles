// Fixed pen palette — drawing colours must be theme-independent so the exported
// PNG looks the same for every viewer regardless of light/dark mode.
export const DRAW_PALETTE = ["#2d2d2d", "#ffffff", "#ff4d4d", "#2d5da1", "#2e9e5b", "#ff8c42"] as const;
// The drawing surface is always this light paper, in both themes, for the same
// reason. Keep in sync with --color-drawing-paper in styles/tokens.css.
export const DRAWING_PAPER = "#fdfbf7";
export const BRUSH_SIZES = [3, 6, 10] as const;
// The lobby doodle sends points as flat x, y pairs, each a fraction of the pad's
// width or height from 0 to PAD_SCALE, so a stroke lands in the same place on every
// pad size. Matches PAD_SCALE in backend/app/rooms/protocol.py.
export const PAD_SCALE = 10_000;
// The lobby doodle's caps, as the server keeps them (MAX_LOBBY_STROKES, MAX_STROKE_POINTS and
// MAX_LOBBY_POINTS in backend/app/rooms/manager.py); points count x, y pairs.
export const LOBBY_MAX_STROKES = 500;
export const LOBBY_MAX_STROKE_POINTS = 4000;
export const LOBBY_MAX_POINTS = 20_000;

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
