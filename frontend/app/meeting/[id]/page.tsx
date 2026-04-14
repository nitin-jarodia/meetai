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
import { useMeetingSocket } from "@/hooks/useMeetingSocket";
import {
  actionItemsApi,
  ApiError,
  meetingsApi,
  transcriptsApi,
  type MeetingDetail,
  type MeetingProcessingJob,
  type MeetingTranscript,
} from "@/services/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function MeetingRoomPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const token = useRequireAuth();
  const [detail, setDetail] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joinRequired, setJoinRequired] = useState(false);
  const [joining, setJoining] = useState(false);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [editingTranscriptId, setEditingTranscriptId] = useState<string | null>(null);
  const [editedTranscriptText, setEditedTranscriptText] = useState("");
  const [savingTranscriptId, setSavingTranscriptId] = useState<string | null>(null);
  const [regeneratingTranscriptId, setRegeneratingTranscriptId] = useState<string | null>(
    null
  );
  const [savingActionItemId, setSavingActionItemId] = useState<string | null>(null);
  const [actionItemError, setActionItemError] = useState<string | null>(null);
  const [transcriptActionError, setTranscriptActionError] = useState<string | null>(null);
  const [transcriptActionMessage, setTranscriptActionMessage] = useState<string | null>(
    null
  );
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [qaHistory, setQaHistory] = useState<
    Array<{
      id?: string;
      question: string;
      answer: string;
      asked_by?: string | null;
      created_at?: string;
    }>
  >([]);

  async function loadMeeting() {
    if (!token || !id) return;
    try {
      const d = await meetingsApi.get(token, id);
      setDetail(d);
      setQaHistory(
        d.qa_history.map((entry) => ({
          id: entry.id,
          question: entry.question,
          answer: entry.answer,
          asked_by: entry.asked_by.full_name || entry.asked_by.email,
          created_at: entry.created_at,
        }))
      );
      setJoinRequired(false);
      setError(null);
      if (!activeJobId && d.processing_jobs[0]?.status !== "completed") {
        setActiveJobId(d.processing_jobs[0]?.id ?? null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setJoinRequired(true);
        setError(null);
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load meeting");
    }
  }

  useEffect(() => {
    void loadMeeting();
    // `loadMeeting` reads current state and should rerun on token/id changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, id]);

  const { connected: socketConnected } = useMeetingSocket(
    id,
    token ?? undefined,
    (event) => {
    if (event.type === "job_updated") {
      const payload = event.job as MeetingProcessingJob;
      setDetail((prev) => {
        if (!prev) return prev;
        const remaining = prev.processing_jobs.filter((job) => job.id !== payload.id);
        return {
          ...prev,
          processing_jobs: [payload, ...remaining],
        };
      });
      setActiveJobId(payload.id);
      if (payload.status === "completed") {
        setUploadMessage("Audio processed successfully. The latest meeting notes are ready.");
        void loadMeeting();
      }
      if (payload.status === "failed") {
        setUploadError(payload.error_message || "Audio processing failed");
      }
    }
    if (event.type === "transcript_ready") {
      setUploadMessage("Audio processed successfully. The latest meeting notes are ready.");
      void loadMeeting();
    }
    if (event.type === "job_failed") {
      setUploadError(event.error);
    }
    }
  );

  async function joinMeeting() {
    if (!token) return;
    setJoining(true);
    try {
      await meetingsApi.join(token, id);
      await loadMeeting();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to join meeting");
    } finally {
      setJoining(false);
    }
  }

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
          id: result.entry.id,
          question: trimmedQuestion,
          answer: result.answer,
          asked_by: result.entry.asked_by.full_name || result.entry.asked_by.email,
          created_at: result.entry.created_at,
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

  function updateJobInDetail(job: MeetingProcessingJob) {
    setDetail((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        processing_jobs: [
          job,
          ...prev.processing_jobs.filter((existing) => existing.id !== job.id),
        ],
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
      await loadMeeting();
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
  const latestJob = detail?.processing_jobs[0] ?? null;

  function formatMeetingDate(value: string) {
    return new Date(value).toLocaleDateString(undefined, {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  async function handleActionItemUpdate(
    itemId: string,
    updates: {
      task?: string | null;
      assigned_to_name?: string | null;
      assigned_user_id?: string | null;
      deadline?: string | null;
      status?: string | null;
    }
  ) {
    if (!token) return;
    setSavingActionItemId(itemId);
    setActionItemError(null);
    try {
      const updated = await actionItemsApi.update(token, itemId, updates);
      setDetail((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          action_items: prev.action_items.map((item) =>
            item.id === itemId ? updated : item
          ),
        };
      });
    } catch (err) {
      setActionItemError(err instanceof Error ? err.message : "Failed to save action item");
    } finally {
      setSavingActionItemId(null);
    }
  }

  async function handleExport(format: "markdown" | "json") {
    if (!token) return;
    try {
      const exported = await meetingsApi.exportNotes(token, id, format);
      const blob = new Blob([exported.content], {
        type: format === "json" ? "application/json" : "text/markdown",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = exported.filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export meeting notes");
    }
  }

  async function handleShare() {
    const shareUrl = window.location.href;
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(shareUrl);
      setUploadMessage("Meeting link copied. Teammates can open it and tap Join meeting.");
      return;
    }
    setUploadMessage(`Share this link: ${shareUrl}`);
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

        {joinRequired ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-2xl font-semibold text-slate-900">Join this meeting</h1>
            <p className="mt-2 text-sm text-slate-600">
              You have the meeting link but are not a participant yet.
            </p>
            <button
              type="button"
              onClick={() => void joinMeeting()}
              disabled={joining}
              className="mt-4 rounded-2xl bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {joining ? "Joining…" : "Join meeting"}
            </button>
          </section>
        ) : null}

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
                  <span className="rounded-full bg-slate-100 px-3 py-1">
                    Socket: {socketConnected ? "Live" : "Offline"}
                  </span>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleShare()}
                    className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Copy share link
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExport("markdown")}
                    className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Export Markdown
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExport("json")}
                    className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Export JSON
                  </button>
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
                        const result = await meetingsApi.uploadAudio(token, id, audioFile);
                        updateJobInDetail(result.job);
                        setActiveJobId(result.job.id);
                        setUploadMessage("Audio queued. Live updates will appear here.");
                        setAudioFile(null);
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
                {latestJob ? (
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-sm font-medium text-slate-800">
                      Latest job: {latestJob.stage.replaceAll("_", " ")}
                    </p>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full bg-brand-600 transition-all"
                        style={{ width: `${Math.max(5, latestJob.progress * 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      {latestJob.status} {activeJobId === latestJob.id ? "· tracking live" : ""}
                    </p>
                  </div>
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

            <ActionItemsList
              action_items={detail.action_items}
              participants={detail.participants.map((participant) => participant.user)}
              savingId={savingActionItemId}
              error={actionItemError}
              onUpdate={handleActionItemUpdate}
            />

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

        {!detail && !error && !joinRequired && (
          <p className="text-slate-500">Loading meeting…</p>
        )}
      </div>
    </Shell>
  );
}
