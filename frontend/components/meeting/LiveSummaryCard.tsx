"use client";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface LiveSummaryCardProps {
  summary: string | null;
  updatedAt: string | null;
  charCount: number | null;
  isRecording: boolean;
}

/**
 * Rolling summary card that updates while the meeting is live.
 * Only visible once the backend has emitted its first `live_summary_updated` event.
 */
export function LiveSummaryCard({
  summary,
  updatedAt,
  charCount,
  isRecording,
}: LiveSummaryCardProps) {
  if (!summary) return null;

  return (
    <Card className="space-y-3 border-brand-primary/25 bg-brand-primaryDim/30">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              isRecording ? "animate-pulse bg-brand-primary" : "bg-text-muted"
            }`}
            aria-hidden
          />
          <p className="text-sm font-semibold text-text-primary">Rolling summary</p>
        </div>
        <Badge variant="info">Live</Badge>
      </div>
      <p className="whitespace-pre-wrap text-sm text-text-secondary">{summary}</p>
      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>{charCount ? `${charCount.toLocaleString()} chars analyzed` : ""}</span>
        {updatedAt ? <span>Updated {formatRelative(updatedAt)}</span> : null}
      </div>
    </Card>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - Date.parse(iso);
  if (!Number.isFinite(diff) || diff < 0) return "just now";
  const s = Math.round(diff / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  return `${h}h ago`;
}
