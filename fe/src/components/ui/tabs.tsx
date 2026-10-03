import { Tabs as BaseTabs } from "@base-ui/react/tabs";

export const Tabs = BaseTabs.Root;
export function TabsList(props: BaseTabs.List.Props) { return <BaseTabs.List {...props} className={`flex gap-1 border-b border-stone-200 ${props.className ?? ""}`} />; }
export function TabsTrigger(props: BaseTabs.Tab.Props) { return <BaseTabs.Tab {...props} className={`rounded-t-md px-3 py-2 text-sm text-stone-600 outline-none data-[selected]:border-b-2 data-[selected]:border-emerald-700 data-[selected]:font-medium data-[selected]:text-stone-900 focus-visible:ring-2 focus-visible:ring-emerald-600 ${props.className ?? ""}`} />; }
export function TabsContent(props: BaseTabs.Panel.Props) { return <BaseTabs.Panel {...props} className={`outline-none ${props.className ?? ""}`} />; }
