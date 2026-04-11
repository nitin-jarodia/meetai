"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { getWebSocketBaseUrl } from "@/lib/publicApi";
import { meetingsApi, type MeetingDetail } from "@/services/api";
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
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [qaHistory, setQaHistory] = useState<
    Array<{ question: string; answer: string }>
  >([]);
  const [lastUpload, setLastUpload] = useState<{
    transcript: string;
    summary: string;
    key_points: string[];
    action_items: Array<{
      task: string;
      assigned_to: string | null;
      deadline: string | null;
    }>;
  } | null>(null);

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
                    setLastUpload(null);
                    try {
                      const result = await meetingsApi.uploadAudio(token, id, audioFile);
                      setLastUpload(result);
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
              {lastUpload && (
                <div className="mt-6 space-y-4 border-t border-slate-100 pt-4">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      AI summary
                    </h3>
                    <div className="mt-2 whitespace-pre-wrap rounded-md bg-emerald-50 p-3 text-sm text-slate-800">
                      {lastUpload.summary}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Key points
                    </h3>
                    {lastUpload.key_points.length === 0 ? (
                      <p className="mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-500">
                        No key points extracted.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
                        {lastUpload.key_points.map((point, index) => (
                          <li key={`${point}-${index}`}>• {point}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Action items
                    </h3>
                    {lastUpload.action_items.length === 0 ? (
                      <p className="mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-500">
                        No action items extracted.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
                        {lastUpload.action_items.map((item, index) => (
                          <li key={`${item.task}-${index}`}>
                            <span className="font-medium text-slate-800">{item.task}</span>
                            {item.assigned_to ? ` — ${item.assigned_to}` : ""}
                            {item.deadline ? ` (Due: ${item.deadline})` : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Transcript
                    </h3>
                    <p className="mt-2 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-700">
                      {lastUpload.transcript}
                    </p>
                  </div>
                </div>
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
              <h2 className="text-sm font-medium text-slate-800">Transcripts</h2>
              {detail.transcripts.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">No segments stored yet.</p>
              ) : (
                <ul className="mt-2 space-y-3 text-sm">
                  {detail.transcripts.map((t) => (
                    <li
                      key={t.id}
                      className="rounded border border-slate-100 bg-white p-3 shadow-sm"
                    >
                      {t.summary ? (
                        <div className="mb-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                            Summary
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">
                            {t.summary}
                          </p>
                        </div>
                      ) : null}
                      {t.key_points.length > 0 ? (
                        <div className="mb-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Key points
                          </p>
                          <ul className="mt-1 space-y-1 text-slate-700">
                            {t.key_points.map((point, index) => (
                              <li key={`${t.id}-point-${index}`}>• {point}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      {t.action_items.length > 0 ? (
                        <div className="mb-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Action items
                          </p>
                          <ul className="mt-1 space-y-1 text-slate-700">
                            {t.action_items.map((item, index) => (
                              <li key={`${t.id}-action-${index}`}>
                                <span className="font-medium text-slate-800">{item.task}</span>
                                {item.assigned_to ? ` — ${item.assigned_to}` : ""}
                                {item.deadline ? ` (Due: ${item.deadline})` : ""}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Transcript
                        </p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-700">
                          {t.transcript_text}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
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
