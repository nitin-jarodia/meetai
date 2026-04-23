"use client";

import { useMemo, useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ActionItem, User } from "@/services/api";

interface ActionItemsListProps {
  action_items: ActionItem[];
  participants?: User[];
  savingId?: string | null;
  error?: string | null;
  onUpdate?: (
    itemId: string,
    updates: {
      task?: string | null;
      assigned_to_name?: string | null;
      assigned_user_id?: string | null;
      deadline?: string | null;
      due_at?: string | null;
      status?: string | null;
    }
  ) => Promise<void> | void;
}

/**
 * Renders editable meeting action items with a real datetime-local picker bound
 * to `due_at` and a relative-time "Overdue" badge. The freeform `deadline`
 * string remains editable for notes and is still parsed server-side.
 */
export function ActionItemsList({
  action_items,
  participants = [],
  savingId,
  error,
  onUpdate,
}: ActionItemsListProps) {
  const [drafts, setDrafts] = useState<Record<string, ActionItem>>({});

  function getDraft(item: ActionItem): ActionItem {
    if (!item.id) return item;
    return drafts[item.id] ?? item;
  }

  function updateDraft(item: ActionItem, updates: Partial<ActionItem>) {
    if (!item.id) return;
    setDrafts((prev) => ({
      ...prev,
      [item.id as string]: {
        ...getDraft(item),
        ...updates,
      },
    }));
  }

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">Action items</p>
          <p className="mt-1 text-xs text-text-secondary">
            Track follow-ups, assignees, and due dates.
          </p>
        </div>
        <Badge variant="default">{action_items.length}</Badge>
      </div>

      {action_items.length === 0 ? (
        <EmptyState
          icon="M9 12l2 2 4-4M5 5h14v14H5z"
          title="No action items yet"
          description="Tasks extracted from the meeting will appear here."
        />
      ) : (
        <div className="space-y-3">
          {action_items.map((item, index) => {
            const draft = getDraft(item);
            const checked = (draft.status ?? "open") === "done";
            const assignedName = draft.assigned_to || "Unassigned";
            const dueAtLocal = toDatetimeLocal(draft.due_at ?? null);
            const overdue =
              !checked && isOverdue(draft.due_at ?? null, draft.deadline ?? null);
            const dueLabel = formatDueLabel(draft.due_at ?? null, draft.deadline ?? null);
            return (
              <div
                key={item.id ?? `${item.task}-${index}`}
                className={`rounded-xl border bg-background-elevated p-4 transition ${
                  overdue
                    ? "border-semantic-danger/40 shadow-[0_0_0_1px_rgba(239,68,68,0.12)]"
                    : "border-background-border"
                }`}
              >
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      item.id && onUpdate
                        ? void onUpdate(item.id, { status: checked ? "open" : "done" })
                        : undefined
                    }
                    className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border ${
                      checked
                        ? "border-brand-primary bg-brand-primary text-white"
                        : "border-background-border bg-transparent text-transparent"
                    }`}
                  >
                    <svg
                      viewBox="0 0 16 16"
                      className="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        d="M3.5 8.5 6.5 11.5 12.5 4.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                  <div className="min-w-0 flex-1 space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <textarea
                        value={draft.task}
                        onChange={(e) => updateDraft(item, { task: e.target.value })}
                        className={`min-h-16 w-full flex-1 rounded-md border border-background-border bg-background-surface px-3 py-2 text-sm ${
                          checked ? "line-through text-text-muted" : "text-text-primary"
                        }`}
                        disabled={!item.id || !onUpdate}
                      />
                      {overdue ? <Badge variant="danger">Overdue</Badge> : null}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <select
                        value={draft.assigned_user_id ?? ""}
                        onChange={(e) => {
                          const assignedUser = participants.find(
                            (p) => p.id === e.target.value
                          );
                          updateDraft(item, {
                            assigned_user_id: e.target.value || null,
                            assigned_to: assignedUser
                              ? assignedUser.full_name || assignedUser.email
                              : null,
                          });
                        }}
                        className="rounded-md border border-background-border bg-background-surface px-3 py-2 text-sm text-text-secondary"
                        disabled={!item.id || !onUpdate}
                      >
                        <option value="">Unassigned</option>
                        {participants.map((participant) => (
                          <option key={participant.id} value={participant.id}>
                            {participant.full_name || participant.email}
                          </option>
                        ))}
                      </select>
                      <input
                        type="datetime-local"
                        value={dueAtLocal}
                        onChange={(e) =>
                          updateDraft(item, {
                            due_at: fromDatetimeLocal(e.target.value),
                          })
                        }
                        className="rounded-md border border-background-border bg-background-surface px-3 py-2 text-sm text-text-secondary placeholder:text-text-muted"
                        disabled={!item.id || !onUpdate}
                      />
                      <select
                        value={draft.status ?? "open"}
                        onChange={(e) => updateDraft(item, { status: e.target.value })}
                        className="rounded-md border border-background-border bg-background-surface px-3 py-2 text-sm text-text-secondary"
                        disabled={!item.id || !onUpdate}
                      >
                        <option value="open">Open</option>
                        <option value="in_progress">In progress</option>
                        <option value="done">Done</option>
                        <option value="blocked">Blocked</option>
                      </select>
                    </div>
                    <input
                      type="text"
                      value={draft.deadline ?? ""}
                      onChange={(e) => updateDraft(item, { deadline: e.target.value })}
                      placeholder={'Freeform deadline (e.g. "next Friday")'}
                      className="w-full rounded-md border border-background-border bg-background-surface px-3 py-2 text-xs text-text-secondary placeholder:text-text-muted"
                      disabled={!item.id || !onUpdate}
                    />
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-3 text-xs text-text-muted">
                        <span className="flex items-center gap-2">
                          <Avatar name={assignedName} size="sm" />
                          {assignedName}
                        </span>
                        {dueLabel ? (
                          <span className={overdue ? "text-semantic-danger" : ""}>
                            {dueLabel}
                          </span>
                        ) : null}
                      </div>
                      {item.id && onUpdate ? (
                        <Button
                          type="button"
                          size="sm"
                          onClick={() =>
                            void onUpdate(item.id as string, {
                              task: draft.task,
                              assigned_user_id: draft.assigned_user_id ?? null,
                              assigned_to_name: draft.assigned_to ?? null,
                              deadline: draft.deadline ?? null,
                              due_at: draft.due_at ?? null,
                              status: draft.status ?? "open",
                            })
                          }
                          loading={savingId === item.id}
                        >
                          Save
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {error ? <p className="text-sm text-semantic-danger">{error}</p> : null}
    </Card>
  );
}

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const tzOffset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);
}

function fromDatetimeLocal(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function isOverdue(dueAt: string | null, deadline: string | null): boolean {
  const parsed = parseDeadline(dueAt, deadline);
  return parsed !== null && parsed < Date.now();
}

function parseDeadline(dueAt: string | null, deadline: string | null): number | null {
  const source = dueAt ?? deadline;
  if (!source) return null;
  const parsed = Date.parse(source);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatDueLabel(dueAt: string | null, deadline: string | null): string | null {
  const parsed = parseDeadline(dueAt, deadline);
  if (parsed === null) {
    return deadline && deadline.trim() ? deadline : null;
  }
  const diffMs = parsed - Date.now();
  const absMin = Math.round(Math.abs(diffMs) / 60000);
  const future = diffMs >= 0;
  let rel: string;
  if (absMin < 60) rel = `${absMin}m`;
  else if (absMin < 60 * 24) rel = `${Math.round(absMin / 60)}h`;
  else rel = `${Math.round(absMin / (60 * 24))}d`;
  const when = new Date(parsed).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  return future ? `Due in ${rel} · ${when}` : `Overdue by ${rel} · ${when}`;
}
