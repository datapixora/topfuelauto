import { cn } from "../../lib/utils";
import React from "react";

type Variant = "primary" | "ghost";

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const base =
    variant === "ghost"
      ? "bg-transparent border border-slate-700 text-slate-100 hover:bg-slate-800"
      : "bg-brand-accent text-slate-950 hover:brightness-110";
  return (
    <button
      className={cn("px-3 py-2 rounded-md text-sm font-semibold transition", base, className)}
      {...props}
    />
  );
}
