import { diffWords, diffWordsWithSpace } from "diff";

export function diffVietnameseWords(before: string, after: string) {
  if (typeof Intl.Segmenter !== "undefined") {
    return diffWordsWithSpace(before, after, { intlSegmenter: new Intl.Segmenter("vi", { granularity: "word" }) });
  }
  return diffWords(before, after);
}
