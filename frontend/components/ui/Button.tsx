"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "@/components/ui/Spinner";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "md";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  const variants = {
    primary: "bg-brand-primary text-white hover:bg-brand-primaryHover active:scale-[0.98] shadow-glow",
    ghost: "border border-background-border bg-transparent text-text-secondary hover:bg-background-elevated",
    danger: "bg-semantic-danger text-white hover:brightness-110 active:scale-[0.98]",
  };
  const sizes = { sm: "h-9 px-3 text-sm", md: "h-10 px-4 text-base" };
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-all duration-150 ${variants[variant]} ${sizes[size]} ${disabled || loading ? "cursor-not-allowed opacity-60" : ""} ${className}`}
    >
      {loading ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
}
