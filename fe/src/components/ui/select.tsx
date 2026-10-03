import { Select as BaseSelect } from "@base-ui/react/select";
import type { ReactNode } from "react";

export function Select({ value, onValueChange, options, label }: { value: string; onValueChange: (value: string) => void; options: { value: string; label: string }[]; label: ReactNode }) {
  return <BaseSelect.Root value={value} onValueChange={(next) => { if (next) onValueChange(next); }}><BaseSelect.Trigger className="flex h-9 w-full items-center justify-between rounded-md border border-stone-300 bg-white px-3 text-sm"><BaseSelect.Value>{label}</BaseSelect.Value><BaseSelect.Icon>⌄</BaseSelect.Icon></BaseSelect.Trigger><BaseSelect.Portal><BaseSelect.Positioner className="z-50 outline-none"><BaseSelect.Popup className="max-h-60 min-w-40 overflow-auto rounded-md border border-stone-200 bg-white p-1 shadow-lg"><BaseSelect.List>{options.map((option) => <BaseSelect.Item key={option.value} value={option.value} className="cursor-pointer rounded px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-stone-100"><BaseSelect.ItemText>{option.label}</BaseSelect.ItemText></BaseSelect.Item>)}</BaseSelect.List></BaseSelect.Popup></BaseSelect.Positioner></BaseSelect.Portal></BaseSelect.Root>;
}
