import { describe, expect, it } from "vitest";

import { SseParser } from "./sse";

describe("SseParser", () => {
  it("đọc event có id, event, data", () => {
    const parser = new SseParser();
    const messages = parser.feed('id: 3\nevent: job.state\ndata: {"seq":3}\n\n');
    expect(messages).toEqual([{ id: "3", event: "job.state", data: '{"seq":3}' }]);
  });

  it("ghép event bị cắt giữa nhiều chunk", () => {
    const parser = new SseParser();
    expect(parser.feed("event: token.delta\nda")).toEqual([]);
    expect(parser.feed('ta: {"text":"Mưa')).toEqual([]);
    expect(parser.feed(' đêm"}\n\n')).toEqual([
      { event: "token.delta", data: '{"text":"Mưa đêm"}' },
    ]);
  });

  it("bỏ qua comment ping và chấp nhận CRLF", () => {
    const parser = new SseParser();
    const messages = parser.feed(": ping\r\n\r\nid: 7\r\ndata: a\r\ndata: b\r\n\r\n");
    expect(messages).toEqual([{ id: "7", event: "message", data: "a\nb" }]);
  });

  it("CR cuối chunk chờ LF của chunk sau", () => {
    const parser = new SseParser();
    expect(parser.feed("data: x\r")).toEqual([]);
    expect(parser.feed("\n\r\n")).toEqual([{ event: "message", data: "x" }]);
  });

  it("giữ id cuối cho event sau không có id (Last-Event-ID)", () => {
    const parser = new SseParser();
    const messages = parser.feed("id: 5\ndata: a\n\ndata: b\n\n");
    expect(messages.map((m) => m.id)).toEqual(["5", "5"]);
  });
});
