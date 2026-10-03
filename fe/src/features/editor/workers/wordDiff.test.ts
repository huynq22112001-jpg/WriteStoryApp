import { describe, expect, it } from "vitest";
import { diffVietnameseWords } from "./wordDiff";

describe("Vietnamese revision word diff", () => {
  it("keeps Vietnamese word boundaries and marks insertions", () => {
    const result = diffVietnameseWords("Cô gái đứng yên.", "Cô gái đứng lặng yên.");
    expect(result.some((part) => part.added && part.value.includes("lặng"))).toBe(true);
  });
});
