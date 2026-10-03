import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ReactElement, ReactNode } from "react";

export function Dialog({ trigger, title, description, children, open, onOpenChange }: { trigger: ReactElement; title: string; description?: string; children: ReactNode; open?: boolean; onOpenChange?: (open: boolean) => void }) {
  return <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
    <BaseDialog.Trigger render={trigger} />
    <BaseDialog.Portal><BaseDialog.Backdrop className="fixed inset-0 z-40 bg-black/30" />
      <BaseDialog.Popup className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,32rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-stone-200 bg-white p-6 shadow-xl">
        <BaseDialog.Title className="text-lg font-semibold">{title}</BaseDialog.Title>
        {description && <BaseDialog.Description className="mt-1 text-sm text-stone-500">{description}</BaseDialog.Description>}
        <div className="mt-5">{children}</div>
      </BaseDialog.Popup>
    </BaseDialog.Portal>
  </BaseDialog.Root>;
}
