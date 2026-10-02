import type { BackendSession } from "@/shared/desktop/bridge";

import type { EventEnvelope } from "./types";

export interface SseMessage {
  event: string;
  data: string;
  id?: string;
}

/**
 * Parser SSE tăng dần (theo đặc tả HTML "event stream interpretation").
 * Dùng fetch streaming thay vì EventSource vì EventSource không gửi được header Authorization
 * (Plan §2 "Streaming FE").
 */
export class SseParser {
  private buffer = "";
  private data: string[] = [];
  private event = "";
  private id: string | undefined;

  feed(chunk: string): SseMessage[] {
    this.buffer += chunk;
    const messages: SseMessage[] = [];
    let newline: number;
    while ((newline = this.buffer.search(/\r\n|\r|\n/)) >= 0) {
      const line = this.buffer.slice(0, newline);
      const sepLength = this.buffer.startsWith("\r\n", newline) ? 2 : 1;
      // "\r" cuối chunk có thể là nửa đầu của "\r\n": chờ chunk sau.
      if (this.buffer[newline] === "\r" && newline + 1 === this.buffer.length) break;
      this.buffer = this.buffer.slice(newline + sepLength);
      const message = this.processLine(line);
      if (message) messages.push(message);
    }
    return messages;
  }

  private processLine(line: string): SseMessage | null {
    if (line === "") {
      if (this.data.length === 0) {
        this.event = "";
        return null;
      }
      const message: SseMessage = { event: this.event || "message", data: this.data.join("\n") };
      if (this.id !== undefined) message.id = this.id;
      this.data = [];
      this.event = "";
      return message;
    }
    if (line.startsWith(":")) return null; // comment / ping
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    switch (field) {
      case "data":
        this.data.push(value);
        break;
      case "event":
        this.event = value;
        break;
      case "id":
        if (!value.includes("\0")) this.id = value;
        break;
      default:
        break;
    }
    return null;
  }
}

export type StreamStatus = "connecting" | "open" | "reconnecting" | "closed";

export interface ConnectEventsOptions {
  session: BackendSession;
  works?: string[];
  signal: AbortSignal;
  onEvent: (envelope: EventEnvelope) => void;
  onStatus?: (status: StreamStatus) => void;
}

const MAX_BACKOFF_MS = 10_000;

/** Kết nối `/v1/events`, tự nối lại bằng `Last-Event-ID` (Plan §23.1.C). */
export async function connectEvents(options: ConnectEventsOptions): Promise<void> {
  const { session, works = [], signal, onEvent, onStatus } = options;
  let lastEventId: string | undefined;
  let backoff = 1000;

  while (!signal.aborted) {
    onStatus?.(lastEventId === undefined ? "connecting" : "reconnecting");
    try {
      const query = works.length ? `?works=${encodeURIComponent(works.join(","))}` : "";
      const headers: Record<string, string> = { Authorization: `Bearer ${session.token}` };
      if (lastEventId !== undefined) headers["Last-Event-ID"] = lastEventId;
      const response = await fetch(`${session.baseUrl}/v1/events${query}`, { headers, signal });
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

      onStatus?.("open");
      backoff = 1000;
      const parser = new SseParser();
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        for (const message of parser.feed(value)) {
          if (message.id !== undefined) lastEventId = message.id;
          onEvent(JSON.parse(message.data) as EventEnvelope);
        }
      }
    } catch (error) {
      if (signal.aborted) break;
      console.warn("Mất kết nối luồng sự kiện", error);
    }
    if (signal.aborted) break;
    onStatus?.("reconnecting");
    await new Promise((resolve) => setTimeout(resolve, backoff));
    backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
  }
  onStatus?.("closed");
}
