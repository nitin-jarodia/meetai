"use client";

import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
}

export function Card({
  children,
  className = "",
  hover = false,
  onClick,
  ...props
}: CardProps) {
  return (
    <div
      {...props}
      onClick={onClick}
      className={`rounded-xl border border-background-border bg-background-surface p-5 shadow-card ${hover ? "cursor-pointer transition-all duration-150 hover:border-background-borderHover hover:bg-background-elevated" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
