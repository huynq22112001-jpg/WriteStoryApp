import { useTranslation } from "react-i18next";

import { useBackendHealth } from "./useBackendHealth";

export function BackendStatusBar() {
  const { t } = useTranslation("boot");
  const { phase, connection } = useBackendHealth();
  const healthy = phase === "ready" && connection === "open";
  const reconnecting = phase === "ready" && connection === "reconnecting";
  const text = healthy ? t("status.connected") : reconnecting ? t("status.reconnecting") : t("status.starting");
  return <div className="border-t border-stone-200 bg-white px-4 py-1 text-xs text-stone-600">{healthy ? "✓" : reconnecting ? "⚠" : "⏳"} {text}</div>;
}
