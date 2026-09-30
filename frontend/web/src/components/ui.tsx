import { clsx, type ClassValue } from "clsx";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
} from "react";

/** Minimal hand-rolled primitives in the shadcn/ui idiom (tokens only, no
 * shadows, hairline borders). Radix-based replacements for anything
 * popup-like arrive with the pages that truly need them (P1+), so the
 * scaffold carries no dependency lock-in. */

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
}) {
  const variants: Record<ButtonVariant, string> = {
    primary: "bg-accent text-accent-ink hover:opacity-90 disabled:opacity-50",
    secondary:
      "bg-raised text-ink border border-line hover:bg-hover disabled:opacity-50",
    ghost: "text-ink-2 hover:bg-hover hover:text-ink disabled:opacity-50",
    danger:
      "border border-danger/40 text-danger hover:bg-danger/10 disabled:opacity-50",
  };
  return (
    <button
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-colors duration-150",
        size === "sm" && "h-8 px-3 text-[13px]",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-lg border border-line bg-raised px-3 text-sm text-ink",
        "placeholder:text-ink-3 focus:border-accent/60",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("mb-1.5 block text-[13px] font-medium text-ink-2", className)}
      {...props}
    />
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-xl border border-line bg-raised p-5", className)}
      {...props}
    />
  );
}

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "accent" | "danger" | "warn" }) {
  const tones = {
    neutral: "border-line text-ink-2",
    accent: "border-accent/40 text-accent",
    danger: "border-danger/40 text-danger",
    warn: "border-warn/40 text-warn",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

export function Separator({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("h-px w-full bg-line-soft", className)} {...props} />;
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("h-4 w-4 animate-spin text-ink-3", className)}
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function ErrorNote({ children, className }: { children: ReactNode; className?: string }) {
  if (children == null) return null;
  return (
    <p role="alert" className={cn("text-[13px] text-danger", className)}>
      {children}
    </p>
  );
}
