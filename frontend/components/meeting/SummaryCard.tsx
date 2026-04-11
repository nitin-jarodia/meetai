type SummaryCardProps = {
  summary?: string | null;
};

export function SummaryCard({ summary }: SummaryCardProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
            Summary
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">Meeting overview</h2>
        </div>
      </div>

      {summary ? (
        <div className="rounded-2xl bg-gradient-to-br from-brand-50 to-emerald-50 p-5">
          <p className="whitespace-pre-wrap text-base leading-7 text-slate-800">{summary}</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-500">
            No summary yet. Upload audio or regenerate the transcript summary to see a
            concise overview here.
          </p>
        </div>
      )}
    </section>
  );
}
