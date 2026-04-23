"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { transcriptsApi, type TranscriptSegment } from "@/services/api";

interface AudioTranscriptPlayerProps {
  token: string;
  transcriptId: string;
  language?: string | null;
  hasAudio: boolean;
  audioUrlOverride?: string | null;
}

/**
 * Streams the meeting audio and keeps a diarized, timestamped transcript in sync
 * with playback. Clicking a segment seeks playback and starts audio if paused.
 */
export function AudioTranscriptPlayer({
  token,
  transcriptId,
  language,
  hasAudio,
  audioUrlOverride,
}: AudioTranscriptPlayerProps) {
  const [segments, setSegments] = useState<TranscriptSegment[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentMs, setCurrentMs] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeSegmentRef = useRef<HTMLButtonElement | null>(null);

  const audioSrc = useMemo(() => {
    if (audioUrlOverride) return audioUrlOverride;
    if (!hasAudio) return null;
    return transcriptsApi.audioUrl(token, transcriptId);
  }, [audioUrlOverride, hasAudio, token, transcriptId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    transcriptsApi
      .segments(token, transcriptId)
      .then((res) => {
        if (cancelled) return;
        setSegments(res.segments);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Failed to load segments");
        setSegments([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, transcriptId]);

  const seekTo = useCallback((ms: number) => {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = Math.max(0, ms / 1000);
    if (el.paused) {
      el.play().catch((err) => {
        setPlaybackError(err instanceof Error ? err.message : "Playback blocked");
      });
    }
  }, []);

  const activeSegment = useMemo(() => {
    if (!segments) return null;
    return (
      segments.find(
        (seg) => currentMs >= seg.start_ms && currentMs <= seg.end_ms
      ) || null
    );
  }, [segments, currentMs]);

  useEffect(() => {
    if (activeSegmentRef.current) {
      activeSegmentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [activeSegment?.id]);

  const speakers = useMemo(() => {
    if (!segments) return [] as string[];
    const set = new Set<string>();
    segments.forEach((s) => set.add(s.speaker_label));
    return Array.from(set);
  }, [segments]);

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-text-primary">Audio playback</p>
          <p className="text-xs text-text-secondary">
            Click any line to jump there. The active line highlights as the audio plays.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {language ? <Badge variant="info">Language: {language}</Badge> : null}
          {speakers.length > 0 ? (
            <Badge variant="default">
              {speakers.length} speaker{speakers.length === 1 ? "" : "s"}
            </Badge>
          ) : null}
        </div>
      </div>

      {audioSrc ? (
        <audio
          ref={audioRef}
          controls
          preload="metadata"
          src={audioSrc}
          className="w-full"
          onTimeUpdate={(e) => setCurrentMs((e.currentTarget.currentTime || 0) * 1000)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onError={() =>
            setPlaybackError(
              "Could not load meeting audio. It may no longer be available on the server."
            )
          }
        >
          Your browser does not support the audio element.
        </audio>
      ) : (
        <div className="rounded-md border border-background-border bg-background-elevated px-4 py-3 text-xs text-text-secondary">
          Audio playback will appear here after you upload a recording.
        </div>
      )}

      {playbackError ? (
        <p className="text-xs text-semantic-danger">{playbackError}</p>
      ) : null}

      <div className="max-h-96 overflow-y-auto rounded-md border border-background-border bg-background-elevated">
        {loading ? (
          <div className="flex items-center gap-2 p-4 text-xs text-text-secondary">
            <Spinner size="sm" />
            Loading segments…
          </div>
        ) : loadError ? (
          <p className="p-4 text-xs text-semantic-danger">{loadError}</p>
        ) : !segments || segments.length === 0 ? (
          <EmptyState
            icon="M9 12l2 2 4-4M5 5h14v14H5z"
            title="No segments yet"
            description="Upload audio to generate diarized, timestamped segments."
          />
        ) : (
          <ol className="divide-y divide-background-border text-sm">
            {segments.map((seg) => {
              const active = activeSegment?.id === seg.id;
              return (
                <li key={seg.id}>
                  <button
                    type="button"
                    ref={active ? activeSegmentRef : undefined}
                    onClick={() => seekTo(seg.start_ms)}
                    className={`flex w-full flex-col items-start gap-1 px-4 py-2 text-left transition ${
                      active
                        ? "bg-brand-primaryDim text-text-primary"
                        : "hover:bg-background-surface text-text-secondary"
                    }`}
                  >
                    <span className="flex items-center gap-2 text-xs text-text-muted">
                      <span className="font-mono">{formatMs(seg.start_ms)}</span>
                      <span className="rounded-full bg-background-surface px-2 py-0.5 text-[11px] text-text-secondary">
                        {seg.speaker_label}
                      </span>
                    </span>
                    <span className="whitespace-pre-wrap leading-6">{seg.text}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>
          {playing ? "Playing" : "Paused"} · {formatMs(currentMs)}
        </span>
        {audioRef.current ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              if (audioRef.current?.paused) {
                void audioRef.current.play().catch(() => {});
              } else {
                audioRef.current?.pause();
              }
            }}
          >
            {playing ? "Pause" : "Play"}
          </Button>
        ) : null}
      </div>
    </Card>
  );
}

function formatMs(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "0:00";
  const total = Math.floor(value / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
