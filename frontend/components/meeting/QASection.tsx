import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

interface QAHistoryItem {
  id?: string;
  question: string;
  answer: string;
  asked_by?: string | null;
  created_at?: string;
}

interface QASectionProps {
  question: string;
  asking: boolean;
  error?: string | null;
  history: QAHistoryItem[];
  disabled?: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function QASection({
  question,
  asking,
  error,
  history,
  disabled = false,
  onQuestionChange,
  onSubmit,
}: QASectionProps) {
  return (
    <Card className="space-y-4">
      <div>
        <p className="text-sm font-semibold text-text-primary">Ask a question</p>
        <p className="mt-1 text-xs text-text-secondary">Ask follow-up questions grounded in the transcript.</p>
      </div>

      <form className="space-y-3" onSubmit={onSubmit}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="text"
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder="Ask anything about this meeting..."
            disabled={asking || disabled}
            className="h-10 flex-1 rounded-md border border-background-border bg-background-surface px-3 text-sm text-text-primary placeholder:text-text-muted"
          />
          <Button type="submit" size="sm" loading={asking} disabled={disabled}>
            {asking ? "Ask" : "Ask"}
          </Button>
        </div>

        {error ? <p className="text-sm text-semantic-danger">{error}</p> : null}
      </form>

      {disabled ? (
        <EmptyState
          icon="M5 12h14M12 5v14"
          title="Transcript required"
          description="Upload a meeting transcript to start asking questions."
        />
      ) : history.length === 0 ? (
        <EmptyState
          icon="M12 4a8 8 0 1 1 0 16 8 8 0 0 1 0-16Zm0 11.2h.01M9.1 9.4a3 3 0 1 1 5.3 1.9c-.86.64-1.4 1.14-1.4 2.1"
          title="No questions yet"
          description="Ask about decisions, deadlines, owners, or blockers."
        />
      ) : (
        <div className="max-h-[300px] space-y-4 overflow-y-auto pr-1">
          {history.map((item, index) => (
            <div key={item.id ?? `${item.question}-${index}`} className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-full bg-brand-primaryDim px-4 py-2 text-sm text-brand-primary">
                  {item.question}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-xl border border-background-border bg-background-elevated px-4 py-3 text-sm text-text-secondary">
                  <p className="leading-6">{item.answer}</p>
                  {item.asked_by || item.created_at ? (
                    <p className="mt-2 text-xs text-text-muted">
                      {item.asked_by ? `Asked by ${item.asked_by}` : null}
                      {item.asked_by && item.created_at ? " · " : null}
                      {item.created_at
                        ? new Date(item.created_at).toLocaleString()
                        : null}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
