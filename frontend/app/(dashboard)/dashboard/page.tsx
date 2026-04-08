"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { meetingsApi, type Meeting } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function DashboardPage() {
  const token = useRequireAuth();
  const clear = useAuthStore((s) => s.clear);
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("meetai-recent-meetings");
    if (raw) {
      try {
        setMeetings(JSON.parse(raw) as Meeting[]);
      } catch {
        /* ignore */
      }
    }
  }, []);

  function persist(next: Meeting[]) {
    setMeetings(next);
    sessionStorage.setItem("meetai-recent-meetings", JSON.stringify(next));
  }

  async function createMeeting(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setCreating(true);
    try {
      const m = await meetingsApi.create(token, { title });
      persist([m, ...meetings.filter((x) => x.id !== m.id)]);
      setTitle("");
      router.push(`/meeting/${m.id}`);
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

        <div>
          <h2 className="text-sm font-medium text-slate-700">Recent (this browser)</h2>
          <ul className="mt-2 space-y-2">
            {meetings.length === 0 && (
              <li className="text-sm text-slate-500">No meetings yet — create one above.</li>
            )}
            {meetings.map((m) => (
              <li key={m.id}>
                <Link
                  href={`/meeting/${m.id}`}
                  className="text-brand-600 hover:underline"
                >
                  {m.title}
                </Link>
                <span className="ml-2 text-xs text-slate-400">{m.id.slice(0, 8)}…</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Shell>
  );
}
