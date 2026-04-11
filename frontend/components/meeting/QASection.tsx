import type { FormEvent } from "react";

type QAHistoryItem = {
  question: string;
  answer: string;
};

type QASectionProps = {
  question: string;
  asking: boolean;
  error?: string | null;
  history: QAHistoryItem[];
  disabled?: boolean;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

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
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          AI Q&amp;A
        </p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">Ask about this meeting</h2>
        <p className="mt-1 text-sm text-slate-500">
          Ask follow-up questions and get concise answers grounded in the transcript.
        </p>
      </div>

      <form className="space-y-3" onSubmit={onSubmit}>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder="Ask anything about this meeting..."
            disabled={asking || disabled}
            className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-500"
          />
          <button
            type="submit"
            disabled={asking || disabled}
            className="rounded-2xl bg-brand-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {asking ? "Thinking..." : "Ask AI"}
          </button>
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </form>

      {disabled ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-500">
            Upload a meeting transcript to start asking questions.
          </p>
        </div>
      ) : history.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-500">
            No questions yet. Ask about decisions, deadlines, owners, or blockers.
          </p>
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {history.map((item, index) => (
            <div key={`${item.question}-${index}`} className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl bg-brand-600 px-4 py-3 text-sm text-white shadow-sm">
                  {item.question}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  {item.answer}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
