import { Tooltip as BaseTooltip } from "@base-ui/react/tooltip";
import type { ReactNode } from "react";

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return <BaseTooltip.Provider><BaseTooltip.Root><BaseTooltip.Trigger render={<span className="inline-flex" />}>{children}</BaseTooltip.Trigger><BaseTooltip.Portal><BaseTooltip.Positioner className="z-50"><BaseTooltip.Popup className="rounded bg-stone-900 px-2 py-1 text-xs text-white shadow">{label}</BaseTooltip.Popup></BaseTooltip.Positioner></BaseTooltip.Portal></BaseTooltip.Root></BaseTooltip.Provider>;
}
