import * as React from "react";
import { cn } from "../../lib/utils";

type AlertVariant = "default" | "destructive" | "success";

const variantStyles: Record<AlertVariant, string> = {
  default: "border-slate-800 bg-slate-900 text-slate-100",
  destructive: "border-red-500/60 bg-red-500/10 text-red-100",
  success: "border-emerald-500/60 bg-emerald-500/10 text-emerald-50",
};

export function Alert({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: AlertVariant }) {
  return (
    <div
      role="alert"
      className={cn("w-full rounded-md border px-4 py-3 text-sm", variantStyles[variant], className)}
      {...props}
    />
  );
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("mb-1 font-semibold", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-relaxed", className)} {...props} />;
}
