"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Shell } from "@/components/Shell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { aiApi, type AskAcrossMeetingsResponse } from "@/services/api";

export default function AskAcrossMeetingsPage() {
  const token = useRequireAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<
    Array<{
      id: string;
      question: string;
      response: AskAcrossMeetingsResponse;
      createdAt: string;
    }>
  >([]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const trimmed = question.trim();
    if (!trimmed) {
      setError("Please enter a question.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await aiApi.askAcrossMeetings(token, {
        question: trimmed,
        top_k: 8,
      });
      setHistory((prev) => [
        {
          id: `${Date.now()}-${Math.random()}`,
          question: trimmed,
          response,
          createdAt: new Date().toISOString(),
        },
        ...prev,
      ]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ask question");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Checking session…
      </div>
    );
  }

  return (
    <Shell title="Ask across meetings">
      <div className="page-enter space-y-6">
        <Card className="space-y-3">
          <div className="space-y-1">
            <h1 className="text-lg font-semibold text-text-primary">
              Ask across your meetings
            </h1>
            <p className="text-sm text-text-secondary">
              Ask any question and MeetAI will answer using evidence drawn from every
              meeting transcript in your workspace.
            </p>
          </div>
          <form className="space-y-3" onSubmit={handleSubmit}>
            <textarea
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                if (error) setError(null);
              }}
              placeholder={'e.g. "What did we decide about pricing last month?"'}
              rows={3}
              className="w-full rounded-md border border-background-border bg-background-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
              disabled={loading}
            />
            <div className="flex items-center justify-between gap-3">
              {error ? (
                <p className="text-sm text-semantic-danger">{error}</p>
              ) : (
                <p className="text-xs text-text-muted">
                  Answers include citations you can click to open the source meeting.
                </p>
              )}
              <Button type="submit" loading={loading} disabled={loading}>
                {loading ? "Searching…" : "Ask"}
              </Button>
            </div>
          </form>
        </Card>

        {loading && history.length === 0 ? (
          <Card className="flex items-center gap-3 text-sm text-text-secondary">
            <Spinner size="sm" /> Retrieving relevant passages…
          </Card>
        ) : null}

        {history.length === 0 && !loading ? (
          <Card>
            <EmptyState
              icon="M9 12l2 2 4-4M5 5h14v14H5z"
              title="No questions yet"
              description="Ask a question and we'll pull the answer from every meeting transcript you own."
            />
          </Card>
        ) : null}

        {history.map((entry) => (
          <AnswerCard
            key={entry.id}
            question={entry.question}
            response={entry.response}
            createdAt={entry.createdAt}
          />
        ))}
      </div>
    </Shell>
  );
}

function AnswerCard({
  question,
  response,
  createdAt,
}: {
  question: string;
  response: AskAcrossMeetingsResponse;
  createdAt: string;
}) {
  return (
    <Card className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-text-primary">{question}</p>
        <span className="text-xs text-text-muted">{formatTime(createdAt)}</span>
      </div>
      <div className="whitespace-pre-wrap text-sm leading-6 text-text-primary">
        {response.answer || "No answer could be generated."}
      </div>
      {response.citations.length ? (
        <div className="space-y-2 border-t border-background-border pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            Sources
          </p>
          <ol className="space-y-2">
            {response.citations.map((cite, idx) => (
              <li
                key={`${cite.meeting_id}-${cite.chunk_index}`}
                className="rounded-lg border border-background-border bg-background-elevated p-3 text-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link
                    href={`/meeting/${cite.meeting_id}`}
                    className="text-sm font-medium text-brand-primary hover:underline"
                  >
                    [{idx + 1}] {cite.meeting_title || "Untitled meeting"}
                  </Link>
                  <Badge variant="default">
                    relevance {(cite.score * 100).toFixed(0)}%
                  </Badge>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-xs text-text-secondary">
                  {cite.snippet}
                </p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </Card>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
