export const ALLOWED_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

export function generateRoomCode(length = 6): string {
  let code = ''
  for (let i = 0; i < length; i++) {
    code += ALLOWED_CHARS.charAt(Math.floor(Math.random() * ALLOWED_CHARS.length))
  }
  return code
}
