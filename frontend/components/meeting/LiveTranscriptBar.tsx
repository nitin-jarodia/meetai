"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface LiveTranscriptBarProps {
  isRecording: boolean;
  transcript: string;
  onStart: () => void;
  onStop: () => void;
  error: string | null;
}

export function LiveTranscriptBar({
  isRecording,
  transcript,
  onStart,
  onStop,
  error,
}: LiveTranscriptBarProps) {
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <span
            className={`h-3 w-3 rounded-full ${isRecording ? "animate-pulse bg-semantic-danger" : "bg-text-muted"}`}
          />
          <span className="text-sm font-medium text-text-primary">
            {isRecording ? "Recording" : "Live transcript"}
          </span>
        </div>
        <div className="min-w-0 flex-1 overflow-x-auto rounded-md border border-background-border bg-background-elevated px-3 py-2 text-sm text-text-secondary">
          {transcript || "Click start to begin live transcription"}
        </div>
        <Button type="button" size="sm" onClick={isRecording ? onStop : onStart}>
          {isRecording ? "Stop" : "Start"}
        </Button>
      </div>
      {error ? <p className="mt-3 text-sm text-semantic-danger">{error}</p> : null}
    </Card>
  );
}
