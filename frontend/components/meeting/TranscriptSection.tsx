"use client";

import { useState } from "react";

type TranscriptSectionProps = {
  transcript?: string | null;
  isEditing: boolean;
  editedText: string;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onChange: (value: string) => void;
  onSave: () => void;
  onRegenerate: () => void;
  saving: boolean;
  regenerating: boolean;
  message?: string | null;
  error?: string | null;
};

export function TranscriptSection({
  transcript,
  isEditing,
  editedText,
  onStartEdit,
  onCancelEdit,
  onChange,
  onSave,
  onRegenerate,
  saving,
  regenerating,
  message,
  error,
}: TranscriptSectionProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Transcript
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">Cleaned transcript</h2>
          <p className="mt-1 text-sm text-slate-500">
            Review, edit, and regenerate the summary from the latest cleaned transcript.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        >
          {isOpen ? "Hide Transcript" : "Show Transcript"}
        </button>
      </div>

      {message ? (
        <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}

      <div
        className={`grid transition-all duration-300 ease-out ${
          isOpen ? "mt-4 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          {transcript ? (
            <div className="space-y-4 border-t border-slate-100 pt-4">
              <div className="flex flex-wrap gap-2">
                {isEditing ? (
                  <>
                    <button
                      type="button"
                      onClick={onCancelEdit}
                      disabled={saving}
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={onSave}
                      disabled={saving}
                      className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={onStartEdit}
                    className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                  >
                    Edit Transcript
                  </button>
                )}

                <button
                  type="button"
                  onClick={onRegenerate}
                  disabled={regenerating}
                  className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {regenerating ? "Regenerating..." : "Regenerate Summary"}
                </button>
              </div>

              <textarea
                rows={10}
                value={isEditing ? editedText : transcript}
                onChange={(e) => onChange(e.target.value)}
                disabled={!isEditing}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-700 outline-none transition focus:border-brand-500 disabled:cursor-text disabled:opacity-100"
              />
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
              <p className="text-sm text-slate-500">
                No cleaned transcript is available yet. Upload meeting audio to generate one.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
