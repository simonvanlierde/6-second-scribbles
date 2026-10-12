// The backend drops any WebSocket frame over 64 KiB (ws_max_message_bytes), and
// the data URL travels inside a JSON message, so keep a margin under that.
export const MAX_DRAWING_CHARS = 56 * 1024;

// Longest side, in pixels, of each attempt. The guessing view shows a drawing at
// most about 1000 CSS px wide, so 1024 px is enough; a HiDPI canvas is often
// twice that. Smaller sizes are only used when a dense drawing is over budget.
const SIDES = [1024, 800, 640, 512, 384];
const QUALITIES = [0.8, 0.5];

// Best compression first. Safari cannot encode WebP; JPEG works there because
// the drawing is painted on an opaque background.
const LOSSY_TYPES = ["image/webp", "image/jpeg"];

function encodeCanvas(canvas: HTMLCanvasElement, quality: number): string {
  for (const type of LOSSY_TYPES) {
    // A browser that cannot encode a type returns a PNG instead of failing.
    const dataUrl = canvas.toDataURL(type, quality);
    if (dataUrl.startsWith(`data:${type}`)) return dataUrl;
  }
  return canvas.toDataURL("image/png");
}

/**
 * Encode a finished drawing as a data URL that fits in one WebSocket message.
 *
 * The strokes are painted over `background` (the colour the drawer saw):
 * WebP compresses the alpha channel losslessly, so a transparent image of a
 * busy drawing is about 1.5x the size of an opaque one, and JPEG has no alpha.
 * Tries WebP, then JPEG, then PNG. If nothing fits, the smallest attempt is
 * returned.
 */
export function encodeDrawing(source: HTMLCanvasElement, background: string): string {
  const longest = Math.max(source.width, source.height, 1);
  // A canvas already under a step is tried at its own size first, then smaller.
  const sides = [...new Set(SIDES.map((side) => Math.min(side, longest)))];
  let smallest = "";
  for (const side of sides) {
    const scale = side / longest;
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(source.width * scale));
    canvas.height = Math.max(1, Math.round(source.height * scale));
    const ctx = canvas.getContext("2d");
    if (!ctx) return source.toDataURL("image/png");
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);

    for (const quality of QUALITIES) {
      const dataUrl = encodeCanvas(canvas, quality);
      if (dataUrl.length <= MAX_DRAWING_CHARS) return dataUrl;
      if (!smallest || dataUrl.length < smallest.length) smallest = dataUrl;
      // PNG ignores quality, so only a smaller size can help.
      if (dataUrl.startsWith("data:image/png")) break;
    }
  }
  return smallest;
}
