import { describe, expect, it } from "vitest";

import { countVietnameseSyllables, normalizeVietnameseText } from "./index";

describe("Vietnamese text utilities (parity with AI language pack)", () => {
  it.each([
    ["Lâm Phong siết chặt chuôi kiếm", 6],
    ["— Đi thôi! — hắn nói … rồi bước ra.", 7],
    ["Nguyễn Văn Ộc người ơi", 5],
    ["Có 10.000 binh mã", 4],
    ["  \n\t ", 0],
  ])("counts syllables in %j", (text, count) => {
    expect(countVietnameseSyllables(text)).toBe(count);
  });

  it("normalizes NFD, line endings, special spaces, zero width, and trailing spaces", () => {
    const raw = "Dòng một\u00a0có NBSP  \r\nDòng\u200b hai\r";
    expect(normalizeVietnameseText(raw)).toBe("Dòng một có NBSP\nDòng hai\n");
    expect(normalizeVietnameseText("Thủy Mặc".normalize("NFD"))).toBe("Thủy Mặc");
  });

  it("does not change tone mark style", () => {
    expect(normalizeVietnameseText("hoà hòa")).toBe("hoà hòa");
  });
});
