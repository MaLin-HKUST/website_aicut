import { forwardRef, InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-2xl border border-border bg-white px-4 text-sm text-foreground outline-none transition placeholder:text-stone-400 focus:border-accent focus:ring-2 focus:ring-accent/20",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";

