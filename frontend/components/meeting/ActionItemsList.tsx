"use client";

import { useState } from "react";
import type { ActionItem, User } from "@/services/api";

type ActionItemsListProps = {
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
      status?: string | null;
    }
  ) => Promise<void> | void;
};

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
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          Action Items
        </p>
        <h2 className="mt-1 text-lg font-semibold text-slate-900">What needs follow-up</h2>
      </div>

      {action_items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5">
          <p className="text-sm text-slate-500">No action items were extracted yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {action_items.map((item, index) => {
            const draft = getDraft(item);
            return (
              <div
                key={item.id ?? `${item.task}-${index}`}
                className="rounded-2xl border border-slate-100 bg-slate-50 p-4"
              >
                <textarea
                  value={draft.task}
                  onChange={(e) => updateDraft(item, { task: e.target.value })}
                  className="min-h-20 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
                  disabled={!item.id || !onUpdate}
                />
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <select
                    value={draft.assigned_user_id ?? ""}
                    onChange={(e) => {
                      const assignedUser = participants.find(
                        (participant) => participant.id === e.target.value
                      );
                      updateDraft(item, {
                        assigned_user_id: e.target.value || null,
                        assigned_to: assignedUser
                          ? assignedUser.full_name || assignedUser.email
                          : draft.assigned_to,
                      });
                    }}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
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
                    type="text"
                    value={draft.deadline ?? ""}
                    onChange={(e) => updateDraft(item, { deadline: e.target.value })}
                    placeholder="Deadline"
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    disabled={!item.id || !onUpdate}
                  />
                  <select
                    value={draft.status ?? "open"}
                    onChange={(e) => updateDraft(item, { status: e.target.value })}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    disabled={!item.id || !onUpdate}
                  >
                    <option value="open">Open</option>
                    <option value="in_progress">In progress</option>
                    <option value="done">Done</option>
                    <option value="blocked">Blocked</option>
                  </select>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <p className="text-sm text-slate-500">
                    Owner: {draft.assigned_to || "Unassigned"}
                  </p>
                  {item.id && onUpdate ? (
                    <button
                      type="button"
                      onClick={() =>
                        void onUpdate(item.id as string, {
                          task: draft.task,
                          assigned_user_id: draft.assigned_user_id ?? null,
                          assigned_to_name: draft.assigned_to ?? null,
                          deadline: draft.deadline ?? null,
                          status: draft.status ?? "open",
                        })
                      }
                      disabled={savingId === item.id}
                      className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
                    >
                      {savingId === item.id ? "Saving…" : "Save"}
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    </section>
  );
}
