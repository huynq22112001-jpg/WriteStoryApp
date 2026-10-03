import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useBootStore } from "./store";

export function ConnectionBanner() {
  const { t } = useTranslation("boot");
  const connection = useBootStore((store) => store.connection);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (connection !== "reconnecting") {
      setVisible(false);
      return;
    }
    const timer = window.setTimeout(() => setVisible(true), 2000);
    return () => window.clearTimeout(timer);
  }, [connection]);

  if (!visible) return null;
  return <div role="status" className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-950">⚠ {t("banner.reconnecting")}</div>;
}
