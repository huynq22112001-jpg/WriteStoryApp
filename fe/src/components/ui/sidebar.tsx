import type { HTMLAttributes, ReactNode } from "react";

export function Sidebar({ children, className = "", ...props }: HTMLAttributes<HTMLElement>) { return <aside {...props} className={`flex min-h-0 flex-col border-r border-stone-200 bg-white ${className}`}>{children}</aside>; }
export function SidebarHeader({ children }: { children: ReactNode }) { return <div className="border-b border-stone-200 p-3">{children}</div>; }
export function SidebarContent({ children }: { children: ReactNode }) { return <div className="min-h-0 flex-1 overflow-auto p-2">{children}</div>; }
export function SidebarMenuButton({ children, active = false, ...props }: HTMLAttributes<HTMLButtonElement> & { active?: boolean }) { return <button type="button" {...props} className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm ${active ? "bg-stone-900 text-white" : "hover:bg-stone-100"} ${props.className ?? ""}`}>{children}</button>; }
