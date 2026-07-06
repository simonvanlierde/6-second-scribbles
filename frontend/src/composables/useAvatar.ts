export const AVATAR_COLORS = [
  "var(--avatar-1)",
  "var(--avatar-2)",
  "var(--avatar-3)",
  "var(--avatar-4)",
  "var(--avatar-5)",
  "var(--avatar-6)",
] as const;

export type AvatarColor = (typeof AVATAR_COLORS)[number];

/** Hash a player id into a stable index in [0, AVATAR_COLORS.length). */
function hash(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i += 1) {
    // biome-ignore lint/suspicious/noBitwiseOperators: `>>> 0` coerces the running hash to a uint32.
    h = (h * 31 + id.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function getAvatarColor(playerId: string): AvatarColor {
  const idx = hash(playerId) % AVATAR_COLORS.length;
  // Non-null: AVATAR_COLORS has length 6, idx is always in range.
  return AVATAR_COLORS[idx] as AvatarColor;
}

export function getAvatarInitial(name: string): string {
  const trimmed = name.trim();
  if (trimmed.length === 0) return "?";
  return trimmed.charAt(0).toUpperCase();
}
