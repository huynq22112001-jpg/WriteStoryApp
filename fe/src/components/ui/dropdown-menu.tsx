import { Menu } from "@base-ui/react/menu";
import type { ReactNode } from "react";

export function DropdownMenu({ trigger, children }: { trigger: ReactNode; children: ReactNode }) {
  return <Menu.Root><Menu.Trigger className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-stone-100">{trigger}</Menu.Trigger><Menu.Portal><Menu.Positioner className="z-50 outline-none"><Menu.Popup className="min-w-40 rounded-md border border-stone-200 bg-white p-1 shadow-lg">{children}</Menu.Popup></Menu.Positioner></Menu.Portal></Menu.Root>;
}
export function DropdownMenuItem(props: Menu.Item.Props) { return <Menu.Item {...props} className={`cursor-pointer rounded px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-stone-100 ${props.className ?? ""}`} />; }
