"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

interface TranscriptSectionProps {
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
}

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
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-text-primary">Transcript</p>
          <p className="mt-1 text-xs text-text-secondary">Review, edit, and refine the latest cleaned transcript.</p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => setIsOpen((prev) => !prev)}>
          {isOpen ? "Hide Transcript" : "Show Transcript"}
        </Button>
      </div>

      {message ? (
        <p className="rounded-md border border-semantic-success/20 bg-semantic-success/10 px-3 py-2 text-sm text-semantic-success">{message}</p>
      ) : null}
      {error ? (
        <p className="rounded-md border border-semantic-danger/20 bg-semantic-danger/10 px-3 py-2 text-sm text-semantic-danger">{error}</p>
      ) : null}

      <div
        className={`grid transition-all duration-250 ease-out ${
          isOpen ? "mt-4 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          {transcript ? (
            <div className="space-y-4 border-t border-background-border pt-4">
              <div className="flex flex-wrap items-center gap-2">
                {isEditing ? (
                  <>
                    <Button type="button" variant="ghost" size="sm" onClick={onCancelEdit} disabled={saving}>
                      Cancel
                    </Button>
                    <Button type="button" size="sm" onClick={onSave} loading={saving}>
                      {saving ? "Saving" : "Save"}
                    </Button>
                  </>
                ) : (
                  <Button type="button" variant="ghost" size="sm" onClick={onStartEdit}>
                    Edit Transcript
                  </Button>
                )}
                <Button type="button" variant="ghost" size="sm" onClick={onRegenerate} loading={regenerating}>
                  {regenerating ? "Regenerating" : "Clean & Regenerate"}
                </Button>
              </div>
              {isEditing ? (
                <textarea
                  rows={12}
                  value={editedText}
                  onChange={(e) => onChange(e.target.value)}
                  className="min-h-[200px] w-full rounded-md border border-background-border bg-background-elevated px-4 py-3 text-sm leading-7 text-text-primary"
                />
              ) : (
                <div className="rounded-md border border-background-border bg-background-elevated px-4 py-4">
                  <p className="whitespace-pre-wrap text-sm leading-7 text-text-secondary">{transcript}</p>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              icon="M7 4h7l5 5v11a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"
              title="No transcript yet"
              description="Upload meeting audio to generate a cleaned transcript."
            />
          )}
        </div>
      </div>
    </Card>
  );
}
