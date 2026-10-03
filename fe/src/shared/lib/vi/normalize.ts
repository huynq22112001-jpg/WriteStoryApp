const SPACE_LIKE = /[\u00a0\u2000-\u200a\u202f\u205f\u3000]/g;
const ZERO_WIDTH = /[\u200b\u200c\u200d\ufeff]/g;
const TRAILING_SPACE = /[ \t]+(?=\n|$)/g;

/** Mirrors ai/writestory_ai/languages/vi/normalizer.py. */
export function normalizeVietnameseText(text: string): string {
  return text
    .replace(/\r\n?/g, "\n")
    .replace(ZERO_WIDTH, "")
    .replace(SPACE_LIKE, " ")
    .replace(TRAILING_SPACE, "")
    .normalize("NFC");
}
