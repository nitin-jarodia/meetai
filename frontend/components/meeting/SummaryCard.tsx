import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

interface SummaryCardProps {
  summary?: string | null;
  keyPoints?: string[];
}

export function SummaryCard({ summary, keyPoints = [] }: SummaryCardProps) {
  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">AI Summary</p>
          <p className="mt-1 text-xs text-text-secondary">Overview generated from the latest transcript</p>
        </div>
        <Badge variant={summary ? "success" : "default"}>{summary ? "Ready" : "Pending"}</Badge>
      </div>
      {summary ? (
        <div className="space-y-4">
          <p className="whitespace-pre-wrap text-sm leading-7 text-text-secondary">{summary}</p>
          {keyPoints.length ? (
            <ul className="space-y-2">
              {keyPoints.map((point, index) => (
                <li key={`${point}-${index}`} className="flex gap-2 text-xs text-text-secondary">
                  <span className="pt-1 text-brand-primary">●</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <EmptyState
          icon="M4 6.5A2.5 2.5 0 0 1 6.5 4H15l5 5v8.5A2.5 2.5 0 0 1 17.5 20h-11A2.5 2.5 0 0 1 4 17.5Z"
          title="Summary pending"
          description="Upload audio or regenerate the transcript to generate an overview."
        />
      )}
    </Card>
  );
}
