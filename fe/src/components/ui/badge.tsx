import type { HTMLAttributes } from "react";

export function Badge({ className = "", ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span {...props} className={`inline-flex items-center rounded-full border border-stone-200 bg-stone-100 px-2 py-0.5 text-xs text-stone-700 ${className}`} />;
}
