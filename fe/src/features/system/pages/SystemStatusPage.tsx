import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/shared/api/errors";
import { errorMessage } from "@/shared/i18n";

import { useApiClient, useBackendSession, useEventStream, useHealth } from "../hooks/useBackend";

const MOCK_WORKS = ["mock-work-1", "mock-work-2", "mock-work-3"];

export function SystemStatusPage() {
  const { t } = useTranslation();
  const session = useBackendSession();
  const client = useApiClient();
  const health = useHealth();
  const stream = useEventStream(MOCK_WORKS);

  const mockRuns = useMutation({
    mutationFn: () =>
      client!.post("/v1/dev/mock-runs", { works: 3, tokens_per_sec: 25, latency_ms: 300 }),
  });

  if (session.isSuccess && session.data === null) {
    return (
      <section className="mx-auto max-w-5xl p-6">
        <h1 className="mb-4 text-2xl font-semibold">{t("system.title")}</h1>
        <p className="rounded-md bg-amber-50 p-4 text-amber-900">{t("system.noSession")}</p>
      </section>
    );
  }

  const healthError = health.error instanceof ApiError ? health.error : null;

  return (
    <section className="mx-auto grid max-w-5xl gap-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("system.title")}</h1>
        <span className="rounded-full bg-stone-200 px-3 py-1 text-xs" data-testid="stream-status">
          {t(`connection.${stream.status}`)}
        </span>
      </header>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 font-medium">{t("system.backend")}</h2>
        {healthError && (
          <p className="text-red-700">{errorMessage(healthError.code, healthError.message)}</p>
        )}
        {health.data && (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-sm">
            <dt className="text-stone-500">{t("system.fields.appVersion")}</dt>
            <dd>{health.data.app_version}</dd>
            <dt className="text-stone-500">{t("system.fields.protocolVersion")}</dt>
            <dd>{health.data.protocol_version}</dd>
            <dt className="text-stone-500">{t("system.fields.dataId")}</dt>
            <dd>{health.data.data_id ?? "—"}</dd>
            <dt className="text-stone-500">{t("system.fields.startedAt")}</dt>
            <dd>{new Date(health.data.started_at).toLocaleString("vi-VN")}</dd>
            <dt className="text-stone-500">{t("system.fields.pid")}</dt>
            <dd>{health.data.pid}</dd>
          </dl>
        )}
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <h2 className="font-medium">{t("system.streams")}</h2>
            <p className="text-xs text-stone-500">{t("system.mockRunsHint")}</p>
          </div>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            disabled={!client || mockRuns.isPending}
            onClick={() => mockRuns.mutate()}
          >
            {t("system.mockRuns")}
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {MOCK_WORKS.map((work) => (
            <article key={work} className="rounded-md bg-stone-50 p-3">
              <h3 className="mb-1 text-xs font-medium text-stone-500">{work}</h3>
              <p className="font-serif text-sm leading-relaxed">{stream.texts[work] ?? "…"}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="mb-3 font-medium">{t("system.events")}</h2>
        {stream.events.length === 0 ? (
          <p className="text-sm text-stone-500">{t("system.noEvents")}</p>
        ) : (
          <ul className="space-y-1 font-mono text-xs">
            {stream.events.map((e) => (
              <li key={`${e.seq}-${e.type}-${e.ts}`}>
                #{e.seq} {e.type} {e.work_id ?? ""} {JSON.stringify(e.payload)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
