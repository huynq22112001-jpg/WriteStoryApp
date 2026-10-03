import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { BootState } from "@/shared/desktop/bridge";
import { confirmDataRoot, openLogsFolder, pickDataRootFolder, quitApp, restartBackend } from "@/shared/desktop/bridge";

const screenClass = "mx-auto flex min-h-full max-w-2xl flex-col justify-center gap-5 px-6 py-12";
const buttonClass = "w-fit rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-50";
const secondaryButtonClass = "w-fit rounded-md border border-stone-300 px-4 py-2 text-sm hover:bg-stone-100";

export function StartingScreen({ state }: { state: BootState }) {
  const { t } = useTranslation("boot");
  const stage = state.progress?.stage;
  return (
    <main className={screenClass} role="status" aria-live="polite">
      <p className="text-3xl font-semibold">{state.phase === "shutting_down" ? t("starting.closing") : t("starting.title")}</p>
      <p className="text-stone-600">{stage ? t(`starting.stage.${stage}`, { defaultValue: t("starting.stage.default") }) : t("starting.stage.default")}</p>
      <p className="text-sm text-stone-500">{t("starting.longWait")}</p>
    </main>
  );
}

export function DataRootScreen({ state }: { state: BootState }) {
  const { t } = useTranslation("boot");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const path = selectedPath ?? state.data_root ?? "";

  async function chooseFolder() {
    const selected = await pickDataRootFolder();
    if (selected) setSelectedPath(selected);
  }

  async function useFolder(acceptCloudSyncWarning = false) {
    if (!path || busy) return;
    setBusy(true);
    setLocalError(null);
    try {
      await confirmDataRoot(path, acceptCloudSyncWarning);
    } catch (error) {
      const message = String(error);
      if (!acceptCloudSyncWarning && message.includes("DATA_ROOT_CLOUD_SYNC")) {
        if (window.confirm(t("dataRoot.cloudSyncConfirm"))) await useFolder(true);
      } else {
        setLocalError(message);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={screenClass}>
      <div role="alert" className="space-y-2">
        <p className="text-3xl font-semibold">{t("dataRoot.title")}</p>
        <p className="text-stone-600">{state.error?.message ?? t("dataRoot.body")}</p>
      </div>
      {path && <p className="break-all rounded bg-stone-100 p-3 font-mono text-sm">{path}</p>}
      {localError && <p role="alert" className="text-sm text-red-700">{localError}</p>}
      <div className="flex flex-wrap gap-3">
        <button className={buttonClass} onClick={() => void chooseFolder()}>{t("dataRoot.choose")}</button>
        <button className={secondaryButtonClass} disabled={!path || busy} onClick={() => void useFolder()}>
          {busy ? t("dataRoot.working") : t("dataRoot.useThis")}
        </button>
      </div>
      <p className="text-sm text-stone-500">{t("dataRoot.storageNote")}</p>
    </main>
  );
}

export function TranslocatedScreen() {
  const { t } = useTranslation("boot");
  return (
    <main className={screenClass} role="alert">
      <p className="text-3xl font-semibold">{t("translocated.title")}</p>
      <p className="text-stone-600">{t("translocated.body")}</p>
      <button className={buttonClass} onClick={() => void quitApp()}>{t("actions.quit")}</button>
    </main>
  );
}

export function StartupErrorScreen({ state }: { state: BootState }) {
  const { t } = useTranslation("boot");
  const [busy, setBusy] = useState(false);
  const locked = state.phase === "locked_by_other_instance";
  async function retry() {
    setBusy(true);
    try { await restartBackend(); } finally { setBusy(false); }
  }
  return (
    <main className={screenClass} role="alert">
      <p className="text-3xl font-semibold">{locked ? t("error.lockedTitle") : t("error.title")}</p>
      <p className="text-stone-600">{state.error?.message ?? t("error.body")}</p>
      {state.error?.code && <code className="w-fit rounded bg-stone-100 px-2 py-1">{state.error.code}</code>}
      <div className="flex flex-wrap gap-3">
        {!locked && <button className={buttonClass} disabled={busy} onClick={() => void retry()}>{busy ? t("actions.working") : t("actions.retry")}</button>}
        <button className={secondaryButtonClass} onClick={() => void openLogsFolder()}>{t("error.openLogs")}</button>
        <button className={secondaryButtonClass} onClick={() => void quitApp()}>{t("actions.quit")}</button>
      </div>
    </main>
  );
}

export function BackendCrashedScreen({ state }: { state: BootState }) {
  const { t } = useTranslation("boot");
  const [busy, setBusy] = useState(false);
  async function restart() {
    setBusy(true);
    try { await restartBackend(); } finally { setBusy(false); }
  }
  const tail = Array.isArray(state.error?.detail && (state.error.detail as { stderr_tail?: unknown }).stderr_tail)
    ? (state.error!.detail as { stderr_tail: string[] }).stderr_tail.slice(-20)
    : [];
  return (
    <main className={screenClass} role="alert">
      <p className="text-3xl font-semibold">{t("crashed.title")}</p>
      <p className="text-stone-600">{state.error?.message ?? t("crashed.body")}</p>
      {state.error?.code && <code className="w-fit rounded bg-stone-100 px-2 py-1">{state.error.code}</code>}
      <p className="text-sm text-stone-500">{t("crashed.count", { count: state.restart_count })}</p>
      {tail.length > 0 && <details><summary>{t("crashed.logs")}</summary><pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded bg-stone-100 p-3 text-xs">{tail.join("\n")}</pre></details>}
      <div className="flex flex-wrap gap-3">
        <button className={buttonClass} disabled={busy} onClick={() => void restart()}>{busy ? t("actions.working") : t("crashed.restart")}</button>
        {state.restart_count >= 3 && <button className={secondaryButtonClass} onClick={() => void openLogsFolder()}>{t("error.openLogs")}</button>}
        <button className={secondaryButtonClass} onClick={() => void quitApp()}>{t("actions.quit")}</button>
      </div>
    </main>
  );
}
