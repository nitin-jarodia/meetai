"use client";

import { Button } from "@/components/ui/Button";

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-background-border bg-background-elevated/50 px-6 py-10 text-center">
      <svg viewBox="0 0 24 24" className="h-10 w-10 text-text-muted" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d={icon} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="space-y-1">
        <p className="text-sm font-medium text-text-primary">{title}</p>
        <p className="text-sm text-text-secondary">{description}</p>
      </div>
      {action ? (
        <Button variant="ghost" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
