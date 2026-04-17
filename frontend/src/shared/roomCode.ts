export const ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
export const ROOM_CODE_LENGTH = 6;

export function generateRoomCode(length = ROOM_CODE_LENGTH): string {
  let code = "";
  for (let i = 0; i < length; i++) {
    code += ALLOWED_CHARS.charAt(Math.floor(Math.random() * ALLOWED_CHARS.length));
  }
  return code;
}

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
