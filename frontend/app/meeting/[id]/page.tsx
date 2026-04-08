"use client";

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
  const [lastUpload, setLastUpload] = useState<{
    transcript: string;
    summary: string;
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
                      Transcript
                    </h3>
                    <p className="mt-2 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-700">
                      {lastUpload.transcript}
                    </p>
                  </div>
                </div>
              )}
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
                <ul className="mt-2 space-y-2 text-sm">
                  {detail.transcripts.map((t) => (
                    <li key={t.id} className="rounded border border-slate-100 p-2">
                      {t.content}
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
