import { AlertCircle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./button";
import { errorActionLabels, runErrorAction, type ErrorAction } from "@/app/errorActions";

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-stone-300 bg-white px-6 py-12 text-center"><Inbox className="mx-auto size-8 text-stone-400"/><h2 className="mt-3 font-semibold">{title}</h2>{description && <p className="mx-auto mt-1 max-w-lg text-sm text-stone-500">{description}</p>}{action && <div className="mt-5">{action}</div>}</div>;
}

export function ErrorState({ title, description, onRetry, action }: { title: string; description?: string; onRetry?: () => void; action?: ErrorAction }) {
  const selectedAction = action ?? (onRetry ? "retry" : undefined);
  return <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-950"><div className="flex gap-3"><AlertCircle className="mt-0.5 size-5 shrink-0"/><div><h2 className="font-semibold">{title}</h2>{description && <p className="mt-1 text-sm">{description}</p>}{selectedAction && <Button variant="secondary" className="mt-3" onClick={() => runErrorAction(selectedAction, onRetry)}>{errorActionLabels[selectedAction] ?? "Tiếp tục"}</Button>}</div></div></div>;
}
