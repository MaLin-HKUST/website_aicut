import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost";
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-full px-5 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-60",
        variant === "default" && "bg-accent text-white hover:bg-accentDark",
        variant === "secondary" && "bg-white text-foreground ring-1 ring-border hover:bg-stone-50",
        variant === "ghost" && "bg-transparent text-foreground hover:bg-black/5",
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = "Button";

