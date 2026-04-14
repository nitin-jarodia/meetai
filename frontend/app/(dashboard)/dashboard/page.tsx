"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
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
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [meetings, setMeetings] = useState<MeetingDetail[]>([]);
  const [results, setResults] = useState<MeetingSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

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
    }, 300);
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
      const meeting = await meetingsApi.create(token, {
        title,
        description: description.trim() || null,
      });
      const detail = await meetingsApi.get(token, meeting.id);
      setMeetings((prev) => [detail, ...prev.filter((item) => item.id !== meeting.id)]);
      setTitle("");
      setDescription("");
      setShowModal(false);
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

  const currentHour = new Date().getHours();
  const greeting =
    currentHour < 12 ? "Good morning" : currentHour < 18 ? "Good afternoon" : "Good evening";
  const currentUserId = (() => {
    try {
      const payload = token.split(".")[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))) as {
        sub?: string;
      };
      return decoded.sub ?? null;
    } catch {
      return null;
    }
  })();
  const currentUser =
    meetings
      .flatMap((meeting) => meeting.participants.map((participant) => participant.user))
      .find((user) => user.id === currentUserId) ??
    meetings.find((meeting) => meeting.host.id === currentUserId)?.host ??
    null;
  const displayName =
    currentUser?.full_name || currentUser?.email?.split("@")[0] || "there";
  const sidebarUser = currentUser?.email || "Your workspace";
  const visibleMeetings = query.trim() ? [] : meetings;
  const searchResults = query.trim() ? results : [];

  return (
    <Shell
      title="Dashboard"
      sidebarUser={sidebarUser}
      sidebarFooter={
        <Button variant="ghost" size="sm" onClick={logout} className="w-full justify-start">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M15 17l5-5-5-5M20 12H9M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Sign out
        </Button>
      }
    >
      <div className="page-enter flex flex-col gap-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xl font-semibold text-text-primary">
              {greeting}, {displayName}
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              Keep your meetings, notes, and next steps in one place.
            </p>
          </div>
          <Button onClick={() => setShowModal(true)}>
            <span className="text-lg leading-none">+</span>
            New Meeting
          </Button>
        </div>

        <div className="relative">
          <svg viewBox="0 0 24 24" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search meetings, transcripts..."
            className="h-10 w-full rounded-md border border-background-border bg-background-elevated pl-10 pr-4 text-sm text-text-primary placeholder:text-text-muted"
          />
        </div>

        {error ? <p className="text-sm text-semantic-danger">{error}</p> : null}

        {loading && !query.trim() ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Card key={index} className="space-y-4">
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-4 w-24" />
                <div className="flex gap-2">
                  <Skeleton className="h-7 w-7 rounded-full" />
                  <Skeleton className="h-7 w-7 rounded-full" />
                  <Skeleton className="h-7 w-7 rounded-full" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-1/2" />
              </Card>
            ))}
          </div>
        ) : query.trim() ? (
          searchResults.length === 0 ? (
            <EmptyState
              icon="M21 21l-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
              title="No results found"
              description="Try another meeting title, note, or transcript phrase."
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {searchResults.map((result) => (
                <Link key={result.meeting.id} href={`/meeting/${result.meeting.id}`}>
                  <Card hover className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-base font-semibold text-text-primary">
                          {result.meeting.title}
                        </p>
                        <p className="mt-1 text-xs text-text-secondary">
                          Search relevance {Math.round(result.score * 100)}%
                        </p>
                      </div>
                      <Badge variant="info">Match</Badge>
                    </div>
                    <p className="text-sm leading-6 text-text-secondary">{result.snippet}</p>
                  </Card>
                </Link>
              ))}
            </div>
          )
        ) : visibleMeetings.length === 0 ? (
          <EmptyState
            icon="M7 3v3M17 3v3M4 8h16M5 6h14a1 1 0 0 1 1 1v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1Z"
            title="No meetings yet"
            description="Create your first meeting to start capturing notes and actions."
            action={{ label: "Create meeting", onClick: () => setShowModal(true) }}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleMeetings.map((meeting) => {
              const latestTranscript = meeting.transcripts[0];
              const avatars = meeting.participants.slice(0, 3).map((participant) => participant.user);
              const overflow = Math.max(0, meeting.participants.length - avatars.length);
              const createdAt = new Date(meeting.created_at);
              return (
                <Link key={meeting.id} href={`/meeting/${meeting.id}`}>
                  <Card hover className="flex h-full flex-col gap-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-base font-semibold text-text-primary">
                          {meeting.title}
                        </p>
                        <p className="mt-1 text-xs text-text-secondary">
                          {createdAt.toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                          })}{" "}
                          ·{" "}
                          {createdAt.toLocaleTimeString(undefined, {
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                      <Badge variant={latestTranscript ? "success" : "default"}>
                        {latestTranscript ? "Transcribed" : "No transcript"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex -space-x-2">
                        {avatars.map((user) => (
                          <span key={user.id} className="rounded-full ring-2 ring-background-surface">
                            <Avatar name={user.full_name || user.email} size="sm" />
                          </span>
                        ))}
                        {overflow > 0 ? (
                          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-background-border bg-background-elevated text-xs text-text-secondary ring-2 ring-background-surface">
                            +{overflow}
                          </span>
                        ) : null}
                      </div>
                      <span className="text-xs text-text-muted">
                        {meeting.action_items.length} action items
                      </span>
                    </div>
                    <p className="line-clamp-3 text-sm leading-6 text-text-secondary">
                      {latestTranscript?.summary || meeting.description || "No summary yet."}
                    </p>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}

        {showModal ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
            <Card className="w-full max-w-[440px] rounded-xl bg-background-elevated p-6">
              <form onSubmit={createMeeting} className="space-y-4">
                <div>
                  <p className="text-xl font-semibold text-text-primary">Create a meeting</p>
                  <p className="mt-1 text-sm text-text-secondary">
                    Start a workspace for notes, transcripts, and follow-up.
                  </p>
                </div>
                <Input
                  label="Title"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Quarterly planning"
                />
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                    Description
                  </span>
                  <textarea
                    rows={4}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Optional context for the meeting..."
                    className="rounded-md border border-background-border bg-background-surface px-3 py-3 text-sm text-text-primary placeholder:text-text-muted"
                  />
                </label>
                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setShowModal(false);
                      setTitle("");
                      setDescription("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" loading={creating}>
                    {creating ? "Creating" : "Create"}
                  </Button>
                </div>
              </form>
            </Card>
          </div>
        ) : null}
      </div>
    </Shell>
  );
}
