"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { getWebSocketBaseUrl } from "@/lib/publicApi";
import { meetingsApi, transcriptsApi, type MeetingDetail } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function MeetingRoomPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const token = useRequireAuth();
  const rawToken = useAuthStore((s) => s.token);
  const [detail, setDetail] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<string>("idle");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [editingTranscriptId, setEditingTranscriptId] = useState<string | null>(null);
  const [editedTranscriptText, setEditedTranscriptText] = useState("");
  const [savingTranscriptId, setSavingTranscriptId] = useState<string | null>(null);
  const [regeneratingTranscriptId, setRegeneratingTranscriptId] = useState<string | null>(
    null
  );
  const [transcriptActionError, setTranscriptActionError] = useState<string | null>(null);
  const [transcriptActionMessage, setTranscriptActionMessage] = useState<string | null>(
    null
  );
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [qaHistory, setQaHistory] = useState<
    Array<{ question: string; answer: string }>
  >([]);

  useEffect(() => {
    if (!token || !id) return;
    let cancelled = false;
    (async () => {
      try {
        const d = await meetingsApi.get(token, id);
        if (!cancelled) setDetail(d);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load meeting"
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, id]);

  useEffect(() => {
    if (!id || !rawToken) return;
    const url = `${getWebSocketBaseUrl()}/ws/meetings/${id}?token=${encodeURIComponent(rawToken)}`;
    const ws = new WebSocket(url);
    setWsStatus("connecting");
    ws.onopen = () => setWsStatus("connected");
    ws.onerror = () => setWsStatus("error");
    ws.onclose = () => setWsStatus("closed");
    return () => {
      ws.close();
    };
  }, [id, rawToken]);

  async function handleAskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setAskError("Please enter a question.");
      return;
    }

    setAsking(true);
    setAskError(null);
    try {
      const result = await meetingsApi.ask(token, id, trimmedQuestion);
      setQaHistory((prev) => [
        {
          question: trimmedQuestion,
          answer: result.answer,
        },
        ...prev,
      ]);
      setQuestion("");
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Failed to get answer");
    } finally {
      setAsking(false);
    }
  }

  function updateTranscriptInDetail(
    transcriptId: string,
    updates: Partial<MeetingDetail["transcripts"][number]>
  ) {
    setDetail((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        transcripts: prev.transcripts.map((transcript) =>
          transcript.id === transcriptId ? { ...transcript, ...updates } : transcript
        ),
      };
    });
  }

  function formatTranscriptDate(value: string) {
    return new Date(value).toLocaleString();
  }

  function renderTranscriptCard(
    transcript: MeetingDetail["transcripts"][number],
    options?: { compact?: boolean }
  ) {
    const compact = options?.compact ?? false;

    return (
      <div className="rounded border border-slate-100 bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-medium text-slate-800">
              {compact ? "Previous transcript" : "Latest transcript"}
            </h3>
            <p className="text-xs text-slate-400">
              Updated {formatTranscriptDate(transcript.created_at)}
            </p>
          </div>
        </div>

        {transcript.summary ? (
          <div className="mb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
              Summary
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
              {transcript.summary}
            </p>
          </div>
        ) : null}

        {transcript.key_points.length > 0 ? (
          <div className="mb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Key points
            </p>
            <ul className="mt-1 space-y-1 text-sm text-slate-700">
              {transcript.key_points.map((point, index) => (
                <li key={`${transcript.id}-point-${index}`}>• {point}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {transcript.action_items.length > 0 ? (
          <div className="mb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Action items
            </p>
            <ul className="mt-1 space-y-1 text-sm text-slate-700">
              {transcript.action_items.map((item, index) => (
                <li key={`${transcript.id}-action-${index}`}>
                  <span className="font-medium text-slate-800">{item.task}</span>
                  {item.assigned_to ? ` — ${item.assigned_to}` : ""}
                  {item.deadline ? ` (Due: ${item.deadline})` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="mb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Cleaned transcript
            </p>
            <div className="flex flex-wrap gap-2">
              {editingTranscriptId === transcript.id ? (
                <>
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    disabled={savingTranscriptId === transcript.id}
                    className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSaveTranscript(transcript.id)}
                    disabled={savingTranscriptId === transcript.id}
                    className="rounded-md bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {savingTranscriptId === transcript.id ? "Saving…" : "Save"}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() =>
                    handleStartEdit(
                      transcript.id,
                      transcript.cleaned_transcript ?? transcript.transcript_text
                    )
                  }
                  className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Edit
                </button>
              )}
              <button
                type="button"
                onClick={() => handleRegenerateTranscript(transcript.id)}
                disabled={regeneratingTranscriptId === transcript.id}
                className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {regeneratingTranscriptId === transcript.id
                  ? "Regenerating…"
                  : "Regenerate Summary"}
              </button>
            </div>
          </div>
          <textarea
            rows={compact ? 4 : 8}
            value={
              editingTranscriptId === transcript.id
                ? editedTranscriptText
                : transcript.cleaned_transcript ?? transcript.transcript_text
            }
            onChange={(e) => setEditedTranscriptText(e.target.value)}
            disabled={editingTranscriptId !== transcript.id}
            className="mt-2 w-full rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 disabled:cursor-text disabled:opacity-100"
          />
        </div>

        <details className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
            Raw transcript
          </summary>
          <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">
            {transcript.transcript_text}
          </p>
        </details>
      </div>
    );
  }

  function handleStartEdit(transcriptId: string, currentText: string) {
    setEditingTranscriptId(transcriptId);
    setEditedTranscriptText(currentText);
    setTranscriptActionError(null);
    setTranscriptActionMessage(null);
  }

  function handleCancelEdit() {
    setEditingTranscriptId(null);
    setEditedTranscriptText("");
    setTranscriptActionError(null);
  }

  async function handleSaveTranscript(transcriptId: string) {
    if (!token) return;
    const trimmedText = editedTranscriptText.trim();
    if (!trimmedText) {
      setTranscriptActionError("Transcript cannot be empty.");
      return;
    }

    setSavingTranscriptId(transcriptId);
    setTranscriptActionError(null);
    setTranscriptActionMessage(null);
    try {
      const result = await transcriptsApi.update(token, transcriptId, trimmedText);
      updateTranscriptInDetail(transcriptId, { cleaned_transcript: trimmedText });
      setEditingTranscriptId(null);
      setEditedTranscriptText("");
      setTranscriptActionMessage(result.message);
    } catch (err) {
      setTranscriptActionError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSavingTranscriptId(null);
    }
  }

  async function handleRegenerateTranscript(transcriptId: string) {
    if (!token) return;
    setRegeneratingTranscriptId(transcriptId);
    setTranscriptActionError(null);
    setTranscriptActionMessage(null);
    try {
      const result = await transcriptsApi.regenerate(token, transcriptId);
      updateTranscriptInDetail(transcriptId, {
        cleaned_transcript: result.cleaned_transcript,
        summary: result.summary,
        key_points: result.key_points,
        action_items: result.action_items,
      });
      setTranscriptActionMessage("Summary regenerated successfully.");
    } catch (err) {
      setTranscriptActionError(
        err instanceof Error ? err.message : "Failed to regenerate summary"
      );
    } finally {
      setRegeneratingTranscriptId(null);
    }
  }

  const latestTranscript = detail?.transcripts[0] ?? null;
  const olderTranscripts = detail?.transcripts.slice(1) ?? [];

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Checking session…
      </div>
    );
  }

  return (
    <Shell title="Meeting room">
      <div className="space-y-6">
        <Link href="/dashboard" className="text-sm text-brand-600 hover:underline">
          ← Back to dashboard
        </Link>

        {error && (
          <p className="rounded-md bg-red-50 p-3 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        {detail && (
          <>
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{detail.title}</h1>
              {detail.description && (
                <p className="mt-1 text-slate-600">{detail.description}</p>
              )}
              <p className="mt-2 text-xs text-slate-400">
                Host: {detail.host.email} · WebSocket: {wsStatus}
              </p>
            </div>

            <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-sm font-medium text-slate-800">
                Audio → transcript &amp; summary
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Upload a recording (WAV, MP3, M4A, etc.). The server runs Whisper locally
                and Groq for a short summary. Large files may take a minute.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <label className="cursor-pointer rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
                  Choose file
                  <input
                    type="file"
                    accept="audio/*,.mp3,.wav,.m4a,.webm,.ogg,.flac"
                    className="sr-only"
                    disabled={uploading}
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      setAudioFile(f);
                      setUploadError(null);
                    }}
                  />
                </label>
                <span className="text-sm text-slate-600">
                  {audioFile ? audioFile.name : "No file selected"}
                </span>
                <button
                  type="button"
                  disabled={!audioFile || uploading}
                  className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={async () => {
                    if (!audioFile || !token) return;
                    setUploading(true);
                    setUploadError(null);
                    setUploadMessage(null);
                    try {
                      await meetingsApi.uploadAudio(token, id, audioFile);
                      setUploadMessage(
                        "Audio processed successfully. The latest transcript has been updated below."
                      );
                      const refreshed = await meetingsApi.get(token, id);
                      setDetail(refreshed);
                    } catch (err) {
                      setUploadError(
                        err instanceof Error ? err.message : "Upload failed"
                      );
                    } finally {
                      setUploading(false);
                    }
                  }}
                >
                  {uploading ? "Processing…" : "Upload & process"}
                </button>
              </div>
              {uploadError && (
                <p className="mt-3 text-sm text-red-600" role="alert">
                  {uploadError}
                </p>
              )}
              {uploadMessage && (
                <p className="mt-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">
                  {uploadMessage}
                </p>
              )}
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-sm font-medium text-slate-800">Ask AI about this meeting</h2>
              <p className="mt-1 text-sm text-slate-500">
                Ask a question using the latest available transcript for this meeting.
              </p>
              <form className="mt-4 space-y-3" onSubmit={handleAskSubmit}>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => {
                      setQuestion(e.target.value);
                      if (askError) setAskError(null);
                    }}
                    placeholder="Ask anything about this meeting..."
                    disabled={asking}
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-brand-500"
                  />
                  <button
                    type="submit"
                    disabled={asking}
                    className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {asking ? "Asking…" : "Ask AI"}
                  </button>
                </div>
                {askError && (
                  <p className="text-sm text-red-600" role="alert">
                    {askError}
                  </p>
                )}
              </form>

              {qaHistory.length > 0 ? (
                <div className="mt-6 space-y-3 border-t border-slate-100 pt-4">
                  {qaHistory.map((item, index) => (
                    <div
                      key={`${item.question}-${index}`}
                      className="rounded-md border border-slate-100 bg-slate-50 p-4"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Question
                      </p>
                      <p className="mt-1 text-sm text-slate-800">{item.question}</p>
                      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-emerald-800">
                        Answer
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                        {item.answer}
                      </p>
                    </div>
                  ))}
                </div>
              ) : null}
            </section>

            <section>
              <h2 className="text-sm font-medium text-slate-800">Participants</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {detail.participants.map((p) => (
                  <li key={`${p.user_id}-${p.role}`}>
                    {p.user.email}{" "}
                    <span className="text-slate-400">({p.role})</span>
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="text-sm font-medium text-slate-800">Transcript Workspace</h2>
              {transcriptActionMessage && (
                <p className="mt-2 rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">
                  {transcriptActionMessage}
                </p>
              )}
              {transcriptActionError && (
                <p className="mt-2 rounded-md bg-red-50 p-3 text-sm text-red-700" role="alert">
                  {transcriptActionError}
                </p>
              )}
              {!latestTranscript ? (
                <p className="mt-2 text-sm text-slate-500">No segments stored yet.</p>
              ) : (
                <div className="mt-3 space-y-4">
                  {renderTranscriptCard(latestTranscript)}
                  {olderTranscripts.length > 0 ? (
                    <details className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                      <summary className="cursor-pointer text-sm font-medium text-slate-800">
                        Previous transcripts ({olderTranscripts.length})
                      </summary>
                      <div className="mt-4 space-y-3">
                        {olderTranscripts.map((transcript) => (
                          <div key={transcript.id}>{renderTranscriptCard(transcript, { compact: true })}</div>
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
              )}
            </section>
          </>
        )}

        {!detail && !error && (
          <p className="text-slate-500">Loading meeting…</p>
        )}
      </div>
    </Shell>
  );
}
