import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { createApiClient } from "@/shared/api/client";
import { connectEvents, type StreamStatus } from "@/shared/api/sse";
import type { EventEnvelope, HealthResponse } from "@/shared/api/types";
import { getBackendSession } from "@/shared/desktop/bridge";

export function useBackendSession() {
  return useQuery({ queryKey: ["backend-session"], queryFn: getBackendSession, staleTime: Infinity });
}

export function useApiClient() {
  const { data: session } = useBackendSession();
  return useMemo(() => (session ? createApiClient(session) : null), [session]);
}

export function useHealth() {
  const client = useApiClient();
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: () => client!.get<HealthResponse>("/v1/health"),
    enabled: client !== null,
    refetchInterval: 10_000,
  });
}

const MAX_EVENTS = 50;

/** Đăng ký luồng sự kiện chung; `works` là truyện cần nhận `token.delta` đầy đủ. */
export function useEventStream(works: string[] = []) {
  const { data: session } = useBackendSession();
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const [events, setEvents] = useState<EventEnvelope[]>([]);
  const [texts, setTexts] = useState<Record<string, string>>({});
  const worksKey = works.join(",");

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    void connectEvents({
      session,
      works: worksKey ? worksKey.split(",") : [],
      signal: controller.signal,
      onStatus: setStatus,
      onEvent: (envelope) => {
        if (envelope.type === "token.delta" && envelope.work_id) {
          const workId = envelope.work_id;
          const text = String(envelope.payload?.text ?? "");
          setTexts((prev) => ({ ...prev, [workId]: (prev[workId] ?? "") + text }));
          return;
        }
        setEvents((prev) => [envelope, ...prev].slice(0, MAX_EVENTS));
      },
    });
    return () => controller.abort();
  }, [session, worksKey]);

  return { status, events, texts };
}
