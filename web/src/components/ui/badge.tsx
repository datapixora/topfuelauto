import { cn } from "../../lib/utils";
import React from "react";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-200 border border-slate-700",
        className
      )}
      {...props}
    />
  );
}
