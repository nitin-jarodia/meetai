import type { ReactNode } from "react";

interface BadgeProps {
  variant?: "success" | "warning" | "danger" | "info" | "default";
  children: ReactNode;
}

export function Badge({ variant = "default", children }: BadgeProps) {
  const styles = {
    success: "bg-semantic-success/15 text-semantic-success",
    warning: "bg-semantic-warning/15 text-semantic-warning",
    danger: "bg-semantic-danger/15 text-semantic-danger",
    info: "bg-semantic-info/15 text-semantic-info",
    default: "bg-background-elevated text-text-secondary",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${styles[variant]}`}
    >
      {children}
    </span>
  );
}
