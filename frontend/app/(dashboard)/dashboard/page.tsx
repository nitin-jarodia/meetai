"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import {
  meetingsApi,
  type MeetingDetail,
  type MeetingSearchResult,
} from "@/services/api";
import { useAuthStore } from "@/store/authStore";

export default function DashboardPage() {
  const token = useRequireAuth();
  const clear = useAuthStore((s) => s.clear);
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [query, setQuery] = useState("");
  const [meetings, setMeetings] = useState<MeetingDetail[]>([]);
  const [results, setResults] = useState<MeetingSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    void meetingsApi
      .list(token, { limit: 50 })
      .then((response) => {
        if (!cancelled) {
          setMeetings(response.items);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load meetings");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const handle = window.setTimeout(() => {
      void meetingsApi
        .search(token, trimmed, 20)
        .then((response) => {
          if (!cancelled) {
            setResults(response.items);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setResults([]);
          }
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query, token]);

  async function createMeeting(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setCreating(true);
    try {
      const meeting = await meetingsApi.create(token, { title });
      const detail = await meetingsApi.get(token, meeting.id);
      setMeetings((prev) => [detail, ...prev.filter((item) => item.id !== meeting.id)]);
      setTitle("");
      router.push(`/meeting/${meeting.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create meeting"
      );
    } finally {
      setCreating(false);
    }
  }

  function logout() {
    clear();
    router.replace("/login");
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Checking session…
      </div>
    );
  }

  return (
    <Shell title="Dashboard">
      <div className="flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-slate-900">Your meetings</h1>
          <button
            type="button"
            onClick={logout}
            className="text-sm text-slate-600 underline hover:text-slate-900"
          >
            Log out
          </button>
        </div>

        <form
          onSubmit={createMeeting}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <h2 className="text-sm font-medium text-slate-700">New meeting</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              type="text"
              required
              placeholder="Meeting title"
              className="min-w-[200px] flex-1 rounded-md border border-slate-300 px-3 py-2"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </form>

        <section>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-sm font-medium text-slate-700">Meeting history</h2>
              <p className="mt-1 text-sm text-slate-500">
                Search titles and transcript content across your meetings.
              </p>
            </div>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search meetings..."
              className="w-full rounded-md border border-slate-300 px-3 py-2 sm:max-w-sm"
            />
          </div>

          {query.trim() ? (
            <ul className="mt-4 space-y-3">
              {results.length === 0 ? (
                <li className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-slate-500">
                  No matching meetings found.
                </li>
              ) : (
                results.map((result) => (
                  <li
                    key={result.meeting.id}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <Link
                      href={`/meeting/${result.meeting.id}`}
                      className="text-base font-medium text-brand-600 hover:underline"
                    >
                      {result.meeting.title}
                    </Link>
                    <p className="mt-2 text-sm text-slate-600">{result.snippet}</p>
                  </li>
                ))
              )}
            </ul>
          ) : (
            <ul className="mt-4 space-y-3">
              {loading ? (
                <li className="text-sm text-slate-500">Loading meetings…</li>
              ) : meetings.length === 0 ? (
                <li className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-slate-500">
                  No meetings yet. Create one above to get started.
                </li>
              ) : (
                meetings.map((meeting) => {
                  const latestTranscript = meeting.transcripts[0];
                  return (
                    <li
                      key={meeting.id}
                      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <Link
                        href={`/meeting/${meeting.id}`}
                        className="text-base font-medium text-brand-600 hover:underline"
                      >
                        {meeting.title}
                      </Link>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                        <span className="rounded-full bg-slate-100 px-3 py-1">
                          {meeting.participants.length} participants
                        </span>
                        <span className="rounded-full bg-slate-100 px-3 py-1">
                          {meeting.action_items.length} action items
                        </span>
                        <span className="rounded-full bg-slate-100 px-3 py-1">
                          {meeting.qa_history.length} Q&A entries
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-600">
                        {latestTranscript?.summary || meeting.description || "No summary yet."}
                      </p>
                    </li>
                  );
                })
              )}
            </ul>
          )}
        </section>
      </div>
    </Shell>
  );
}
