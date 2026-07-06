export const ROOM_CODE_LENGTH = 6;

export function normalizeRoomCode(code: string): string {
  return String(code || "")
    .trim()
    .toUpperCase();
}

export function isValidRoomCode(code: string, length = ROOM_CODE_LENGTH): boolean {
  const c = normalizeRoomCode(code);
  const re = new RegExp(`^[A-Z0-9]{${length}}$`);
  return re.test(c);
}
