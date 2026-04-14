"use client";

import type { InputHTMLAttributes, ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  hint?: string;
  rightSlot?: ReactNode;
}

export function Input({
  label,
  error,
  hint,
  rightSlot,
  className = "",
  ...props
}: InputProps) {
  return (
    <label className="flex flex-col gap-1.5">
      {label ? (
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          {label}
        </span>
      ) : null}
      <span className="relative">
        <input
          {...props}
          className={`h-10 w-full rounded-md border bg-background-surface px-3 text-sm text-text-primary placeholder:text-text-muted ${rightSlot ? "pr-11" : ""} ${error ? "border-semantic-danger ring-2 ring-semantic-danger/40" : "border-background-border focus:border-brand-primary/60 focus:ring-2 focus:ring-brand-primary/40"} ${className}`}
        />
        {rightSlot ? (
          <span className="absolute inset-y-0 right-3 flex items-center">{rightSlot}</span>
        ) : null}
      </span>
      {error ? <span className="mt-1 text-xs text-semantic-danger">{error}</span> : null}
      {!error && hint ? <span className="text-xs text-text-secondary">{hint}</span> : null}
    </label>
  );
}
