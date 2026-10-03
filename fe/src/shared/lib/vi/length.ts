/** Mirrors ai/writestory_ai/languages/vi/length.py. */
export function countVietnameseSyllables(text: string): number {
  return text
    .normalize("NFC")
    .split(/\s+/u)
    .filter((token) => token.length > 0 && /[\p{L}\p{N}]/u.test(token)).length;
}
