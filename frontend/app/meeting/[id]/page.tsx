"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { ActionItemsList } from "@/components/meeting/ActionItemsList";
import { QASection } from "@/components/meeting/QASection";
import { SummaryCard } from "@/components/meeting/SummaryCard";
import { TranscriptSection } from "@/components/meeting/TranscriptSection";
import {
  meetingsApi,
  transcriptsApi,
  type MeetingDetail,
  type MeetingTranscript,
} from "@/services/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function MeetingRoomPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const token = useRequireAuth();
  const [detail, setDetail] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
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
    updates: Partial<MeetingTranscript>
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
  const visibleTranscript =
    latestTranscript?.cleaned_transcript ?? latestTranscript?.transcript_text ?? "";

  function formatMeetingDate(value: string) {
    return new Date(value).toLocaleDateString(undefined, {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Checking session…
      </div>
    );
  }

  return (
    <Shell title="Meeting details">
      <div className="space-y-8">
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
            <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
                  Meeting
                </p>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
                  {detail.title}
                </h1>
                {detail.description ? (
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                    {detail.description}
                  </p>
                ) : null}

                <div className="mt-5 flex flex-wrap gap-2 text-sm text-slate-600">
                  <span className="rounded-full bg-slate-100 px-3 py-1">
                    {formatMeetingDate(detail.created_at)}
                  </span>
                  <span className="rounded-full bg-slate-100 px-3 py-1">
                    Host: {detail.host.email}
                  </span>
                  <span className="rounded-full bg-slate-100 px-3 py-1">
                    Participants: {detail.participants.length}
                  </span>
                  <span className="rounded-full bg-slate-100 px-3 py-1">
                    Transcript versions: {detail.transcripts.length}
                  </span>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Upload
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-900">
                  Add meeting audio
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Upload a recording to refresh the transcript and AI-generated meeting
                  notes.
                </p>

                <div className="mt-4 space-y-3">
                  <label className="flex cursor-pointer items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-4 text-sm font-medium text-slate-700 transition hover:bg-slate-100">
                    {audioFile ? audioFile.name : "Choose audio file"}
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

                  <button
                    type="button"
                    disabled={!audioFile || uploading}
                    className="w-full rounded-2xl bg-brand-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={async () => {
                      if (!audioFile || !token) return;
                      setUploading(true);
                      setUploadError(null);
                      setUploadMessage(null);
                      try {
                        await meetingsApi.uploadAudio(token, id, audioFile);
                        setUploadMessage(
                          "Audio processed successfully. The latest meeting notes are ready."
                        );
                        setAudioFile(null);
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
                    {uploading ? "Processing..." : "Upload & process"}
                  </button>
                </div>

                {uploadError ? (
                  <p className="mt-3 text-sm text-red-600" role="alert">
                    {uploadError}
                  </p>
                ) : null}
                {uploadMessage ? (
                  <p className="mt-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {uploadMessage}
                  </p>
                ) : null}
              </div>
            </section>

            <SummaryCard summary={latestTranscript?.summary} />

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Key Points
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-900">
                  Important discussion highlights
                </h2>
              </div>

              {latestTranscript?.key_points.length ? (
                <ul className="space-y-3">
                  {latestTranscript.key_points.map((point, index) => (
                    <li
                      key={`${latestTranscript.id}-key-point-${index}`}
                      className="flex gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700"
                    >
                      <span className="mt-1 h-2 w-2 rounded-full bg-brand-500" />
                      <span className="leading-6">{point}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
                  <p className="text-sm text-slate-500">
                    No key points available yet.
                  </p>
                </div>
              )}
            </section>

            <ActionItemsList action_items={latestTranscript?.action_items ?? []} />

            <TranscriptSection
              transcript={visibleTranscript}
              isEditing={editingTranscriptId === latestTranscript?.id}
              editedText={editedTranscriptText}
              onStartEdit={() => {
                if (!latestTranscript) return;
                handleStartEdit(latestTranscript.id, visibleTranscript);
              }}
              onCancelEdit={handleCancelEdit}
              onChange={setEditedTranscriptText}
              onSave={() => {
                if (!latestTranscript) return;
                void handleSaveTranscript(latestTranscript.id);
              }}
              onRegenerate={() => {
                if (!latestTranscript) return;
                void handleRegenerateTranscript(latestTranscript.id);
              }}
              saving={savingTranscriptId === latestTranscript?.id}
              regenerating={regeneratingTranscriptId === latestTranscript?.id}
              message={transcriptActionMessage}
              error={transcriptActionError}
            />

            <QASection
              question={question}
              asking={asking}
              error={askError}
              history={qaHistory}
              disabled={!latestTranscript}
              onQuestionChange={(value) => {
                setQuestion(value);
                if (askError) setAskError(null);
              }}
              onSubmit={handleAskSubmit}
            />
          </>
        )}

        {!detail && !error && (
          <p className="text-slate-500">Loading meeting…</p>
        )}
      </div>
    </Shell>
  );
}
