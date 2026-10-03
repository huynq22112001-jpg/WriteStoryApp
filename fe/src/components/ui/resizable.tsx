import { Group, Panel, Separator } from "react-resizable-panels";
import type { ComponentProps } from "react";

export const ResizablePanelGroup = (props: ComponentProps<typeof Group>) => <Group {...props} className={`flex h-full min-h-0 w-full ${props.className ?? ""}`} />;
export const ResizablePanel = Panel;
export function ResizableHandle(props: ComponentProps<typeof Separator>) { return <Separator {...props} className={`w-1 cursor-col-resize bg-stone-200 transition hover:bg-emerald-600 data-[active]:bg-emerald-700 ${props.className ?? ""}`} />; }
