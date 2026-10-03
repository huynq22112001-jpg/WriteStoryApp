import { Button as BaseButton } from "@base-ui/react/button";
import type { ComponentProps } from "react";

type Props = ComponentProps<typeof BaseButton> & { variant?: "default" | "secondary" | "ghost" | "destructive" };
const variants = {
  default: "bg-stone-900 text-white hover:bg-stone-700",
  secondary: "bg-stone-100 text-stone-900 hover:bg-stone-200",
  ghost: "bg-transparent text-stone-700 hover:bg-stone-100",
  destructive: "bg-red-700 text-white hover:bg-red-800",
};

export function Button({ className = "", variant = "default", ...props }: Props) {
  return <BaseButton {...props} className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`} />;
}
