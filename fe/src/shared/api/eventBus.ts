import type { BackendSession } from "@/shared/desktop/bridge";

import { connectEvents, type StreamStatus } from "./sse";
import type { EventEnvelope } from "./types";

type EventListener = (event: EventEnvelope) => void;
type StatusListener = (status: StreamStatus) => void;

const eventListeners = new Set<EventListener>();
const statusListeners = new Set<StatusListener>();
let controller: AbortController | null = null;
let activeKey: string | null = null;
let status: StreamStatus = "closed";

function publishStatus(next: StreamStatus) {
  status = next;
  statusListeners.forEach((listener) => listener(next));
}

export function startEventBus(session: BackendSession): () => void {
  const key = `${session.base_url}\n${session.token}`;
  if (controller && activeKey === key) return () => {};
  controller?.abort();
  controller = new AbortController();
  activeKey = key;
  void connectEvents({
    session,
    signal: controller.signal,
    onStatus: publishStatus,
    onEvent: (event) => eventListeners.forEach((listener) => listener(event)),
  });
  const owner = controller;
  return () => {
    if (controller !== owner) return;
    owner.abort();
    controller = null;
    activeKey = null;
    publishStatus("closed");
  };
}

export function subscribeEventBus(onEvent: EventListener, onStatus?: StatusListener): () => void {
  eventListeners.add(onEvent);
  if (onStatus) {
    statusListeners.add(onStatus);
    onStatus(status);
  }
  return () => {
    eventListeners.delete(onEvent);
    if (onStatus) statusListeners.delete(onStatus);
  };
}
