"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { ActionItemsList } from "@/components/meeting/ActionItemsList";
import { AudioTranscriptPlayer } from "@/components/meeting/AudioTranscriptPlayer";
import { LiveSummaryCard } from "@/components/meeting/LiveSummaryCard";
import { LiveTranscriptBar } from "@/components/meeting/LiveTranscriptBar";
import { QASection } from "@/components/meeting/QASection";
import { SummaryCard } from "@/components/meeting/SummaryCard";
import { TranscriptSection } from "@/components/meeting/TranscriptSection";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useLiveTranscription } from "@/hooks/useLiveTranscription";
import { useMeetingSocket } from "@/hooks/useMeetingSocket";
import { useToast } from "@/components/ui/Toast";
import { getWebSocketBaseUrl } from "@/lib/publicApi";
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
  const [liveSocket, setLiveSocket] = useState<WebSocket | null>(null);
  const [liveSummary, setLiveSummary] = useState<{
    summary: string;
    updatedAt: string;
    charCount: number | null;
  } | null>(null);
  const { showToast } = useToast();
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

  useEffect(() => {
    if (!id || !token) return;
    const socket = new WebSocket(
      `${getWebSocketBaseUrl()}/ws/meetings/${id}?token=${encodeURIComponent(token)}`
    );
    setLiveSocket(socket);
    return () => {
      socket.close();
      setLiveSocket(null);
    };
  }, [id, token]);

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
    if (event.type === "live_summary_updated") {
      setLiveSummary({
        summary: event.summary,
        updatedAt: new Date().toISOString(),
        charCount: typeof event.char_count === "number" ? event.char_count : null,
      });
    }
    if (event.type === "action_item_due_soon") {
      const task = event.action_item.task || "Action item";
      showToast(`Due soon: ${truncate(task, 80)}`, "info");
    }
    if (event.type === "action_item_overdue") {
      const task = event.action_item.task || "Action item";
      showToast(`Overdue: ${truncate(task, 80)}`, "error");
      void loadMeeting();
    }
    }
  );
  const {
    isRecording,
    transcript: liveTranscript,
    error: liveTranscriptError,
    startRecording,
    stopRecording,
  } = useLiveTranscription(liveSocket);

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

  function truncate(value: string, max: number) {
    if (value.length <= max) return value;
    return `${value.slice(0, max - 1)}…`;
  }

  function formatMeetingDate(value: string) {
    return new Date(value).toLocaleDateString(undefined, {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatCompactDate(value: string) {
    return new Date(value).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function handleActionItemUpdate(
    itemId: string,
    updates: {
      task?: string | null;
      assigned_to_name?: string | null;
      assigned_user_id?: string | null;
      deadline?: string | null;
      due_at?: string | null;
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
    <Shell title={detail?.title || "Meeting details"}>
      <div className="page-enter space-y-6">
        <div className="sticky top-0 z-20 -mx-4 border-b border-background-border bg-background-surface/80 px-4 py-3 backdrop-blur md:-mx-6 md:px-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <Link href="/dashboard" className="text-text-secondary transition-colors hover:text-text-primary">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M15 18 9 12l6-6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-text-primary">
                  {detail?.title || "Meeting details"}
                </p>
                {detail ? (
                  <p className="text-xs text-text-secondary">{formatMeetingDate(detail.created_at)}</p>
                ) : null}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`h-2 w-2 rounded-full ${socketConnected ? "bg-semantic-success" : "bg-text-muted"}`} />
              <details className="relative">
                <summary className="list-none">
                  <Button variant="ghost" size="sm">Export</Button>
                </summary>
                <div className="absolute right-0 mt-2 w-40 rounded-xl border border-background-border bg-background-elevated p-2 shadow-card">
                  <button type="button" onClick={() => void handleExport("markdown")} className="flex w-full rounded-md px-3 py-2 text-left text-sm text-text-secondary transition hover:bg-background-surface hover:text-text-primary">
                    Export Markdown
                  </button>
                  <button type="button" onClick={() => void handleExport("json")} className="flex w-full rounded-md px-3 py-2 text-left text-sm text-text-secondary transition hover:bg-background-surface hover:text-text-primary">
                    Export JSON
                  </button>
                  <button type="button" onClick={() => void handleShare()} className="flex w-full rounded-md px-3 py-2 text-left text-sm text-text-secondary transition hover:bg-background-surface hover:text-text-primary">
                    Copy share link
                  </button>
                </div>
              </details>
              {detail ? (
                <div className="hidden items-center -space-x-2 sm:flex">
                  {detail.participants.slice(0, 3).map((participant) => (
                    <span key={participant.user_id} className="rounded-full ring-2 ring-background-surface">
                      <Avatar name={participant.user.full_name || participant.user.email} size="md" />
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {error ? (
          <p className="rounded-md border border-semantic-danger/20 bg-semantic-danger/10 px-4 py-3 text-sm text-semantic-danger" role="alert">
            {error}
          </p>
        ) : null}

        <LiveTranscriptBar
          isRecording={isRecording}
          transcript={liveTranscript}
          onStart={() => {
            void startRecording();
          }}
          onStop={stopRecording}
          error={liveTranscriptError}
        />

        {joinRequired ? (
          <Card className="space-y-3">
            <p className="text-xl font-semibold text-text-primary">Join this meeting</p>
            <p className="text-sm text-text-secondary">
              You have the invite link but are not a participant yet.
            </p>
            <Button onClick={() => void joinMeeting()} loading={joining}>
              {joining ? "Joining" : "Join meeting"}
            </Button>
          </Card>
        ) : null}

        {!detail && !error && !joinRequired ? (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-4">
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-80 w-full" />
              <Skeleton className="h-72 w-full" />
            </div>
            <div className="space-y-4">
              <Skeleton className="h-56 w-full" />
              <Skeleton className="h-72 w-full" />
              <Skeleton className="h-56 w-full" />
            </div>
          </div>
        ) : null}

        {detail ? (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-4">
              <Card className="space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-text-primary">Audio upload</p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Upload recorded audio to refresh the transcript and summary.
                    </p>
                  </div>
                  <Badge variant={latestJob?.status === "completed" ? "success" : "default"}>
                    {latestJob?.status || "Idle"}
                  </Badge>
                </div>
                <div className="space-y-3">
                  <label className="flex h-24 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-background-border bg-background-elevated text-center transition hover:border-background-borderHover hover:bg-background-surface">
                    <span className="text-sm font-medium text-text-primary">
                      {audioFile ? audioFile.name : "Drop audio here or click to browse"}
                    </span>
                    <span className="mt-1 text-xs text-text-secondary">
                      {audioFile
                        ? `${(audioFile.size / 1024 / 1024).toFixed(2)} MB selected`
                        : "MP3, WAV, M4A, WEBM, OGG, or FLAC"}
                    </span>
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
                  {audioFile ? (
                    <div className="flex items-center justify-between rounded-md border border-background-border bg-background-elevated px-3 py-2 text-sm text-text-secondary">
                      <span className="truncate">{audioFile.name}</span>
                      <button
                        type="button"
                        onClick={() => setAudioFile(null)}
                        className="text-text-muted transition hover:text-text-primary"
                      >
                        Remove
                      </button>
                    </div>
                  ) : null}
                  <Button
                    className="w-full"
                    loading={uploading}
                    disabled={!audioFile || uploading}
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
                        setUploadError(err instanceof Error ? err.message : "Upload failed");
                      } finally {
                        setUploading(false);
                      }
                    }}
                  >
                    {uploading ? "Processing Audio" : "Process Audio"}
                  </Button>
                  <div className="h-1 overflow-hidden rounded-full bg-brand-primaryDim">
                    <div
                      className="h-full rounded-full bg-brand-primary transition-all duration-250"
                      style={{
                        width: `${Math.max(uploading || latestJob ? 8 : 0, (latestJob?.progress ?? 0) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
                {latestJob ? (
                  <div className="flex items-center gap-3 text-sm text-text-secondary">
                    <svg viewBox="0 0 24 24" className="h-4 w-4 animate-[spin_600ms_linear_infinite]" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M12 3a9 9 0 1 0 9 9" strokeLinecap="round" />
                    </svg>
                    <span className="transition-opacity duration-250">
                      {latestJob.stage.replaceAll("_", " ")} · {Math.round(latestJob.progress * 100)}%
                    </span>
                  </div>
                ) : null}
                {uploadError ? <p className="text-sm text-semantic-danger">{uploadError}</p> : null}
                {uploadMessage ? <p className="text-sm text-semantic-success">{uploadMessage}</p> : null}
              </Card>

              <LiveSummaryCard
                summary={liveSummary?.summary ?? null}
                updatedAt={liveSummary?.updatedAt ?? null}
                charCount={liveSummary?.charCount ?? null}
                isRecording={isRecording}
              />

              {latestTranscript ? (
                <AudioTranscriptPlayer
                  token={token}
                  transcriptId={latestTranscript.id}
                  language={latestTranscript.language ?? null}
                  hasAudio={Boolean(latestTranscript.has_audio)}
                />
              ) : null}

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
            </div>

            <div className="space-y-4">
              <SummaryCard
                summary={latestTranscript?.summary}
                keyPoints={latestTranscript?.key_points ?? []}
              />

              <ActionItemsList
                action_items={detail.action_items}
                participants={detail.participants.map((participant) => participant.user)}
                savingId={savingActionItemId}
                error={actionItemError}
                onUpdate={handleActionItemUpdate}
              />

              <Card className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-text-primary">Participants</p>
                  <Badge variant="default">{detail.participants.length}</Badge>
                </div>
                {detail.participants.length ? (
                  <div className="space-y-3">
                    {detail.participants.map((participant) => (
                      <div key={participant.user_id} className="flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-3">
                          <Avatar name={participant.user.full_name || participant.user.email} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate text-sm text-text-primary">
                              {participant.user.full_name || participant.user.email}
                            </p>
                            <p className="truncate text-xs text-text-secondary">
                              {participant.user.email}
                            </p>
                          </div>
                        </div>
                        <Badge variant={participant.role === "host" ? "info" : "default"}>
                          {participant.role}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 7a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7m10 14v-2a4 4 0 0 0-3-3.87M14 4.1a4 4 0 0 1 0 7.8"
                    title="No participants"
                    description="People invited to this meeting will appear here."
                  />
                )}
                {joinRequired ? (
                  <Button className="w-full" onClick={() => void joinMeeting()} loading={joining}>
                    {joining ? "Joining" : "Join meeting"}
                  </Button>
                ) : null}
                <div className="rounded-md border border-background-border bg-background-elevated px-3 py-3 text-xs text-text-secondary">
                  Host: {detail.host.email}
                  <br />
                  Created: {formatCompactDate(detail.created_at)}
                </div>
              </Card>
            </div>
          </div>
        ) : null}
      </div>
    </Shell>
  );
}
