/**
 * Typed fetch helpers for the MeetAI FastAPI backend.
 */

import { getPublicApiBaseUrl } from "@/lib/publicApi";

const API_BASE = getPublicApiBaseUrl();

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return {} as T;
  }
}

/** FastAPI returns `detail` as a string, or as a list of validation errors for 422. */
function formatErrorDetail(data: unknown, statusText: string): string {
  if (!data || typeof data !== "object") {
    return statusText || "Request failed";
  }
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const loc = Array.isArray((item as { loc?: unknown }).loc)
          ? (item as { loc: unknown[] }).loc
              .filter((x) => typeof x === "string" && x !== "body")
              .join(".")
          : "";
        const msg = String((item as { msg: unknown }).msg);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return JSON.stringify(item);
    });
    return parts.join(" ") || statusText || "Request failed";
  }
  if (detail != null) {
    return String(detail);
  }
  return statusText || "Request failed";
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const { token, headers, ...rest } = options;
  const h = new Headers(headers);
  h.set("Content-Type", "application/json");
  if (token) {
    h.set("Authorization", `Bearer ${token}`);
  }
  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { ...rest, headers: h });
  } catch (e) {
    const isNetwork =
      e instanceof TypeError &&
      (e.message === "Failed to fetch" || e.message === "Load failed");
    const hint = isNetwork
      ? ` Cannot reach ${API_BASE}. From the repo, run: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (SQLite needs no Docker; see README).`
      : "";
    const message =
      e instanceof Error ? `${e.message}.${hint}` : `Network error.${hint}`;
    throw new ApiError(message.trim(), 0);
  }
  const data = await parseJson<T & { detail?: string | unknown }>(res);
  if (!res.ok) {
    const detail = formatErrorDetail(data, res.statusText);
    throw new ApiError(detail || "Request failed", res.status, data);
  }
  return data as T;
}

export type TokenResponse = { access_token: string; token_type: string };
export type User = {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
};
export type ActionItem = {
  task: string;
  assigned_to: string | null;
  deadline: string | null;
};
export type Meeting = {
  id: string;
  title: string;
  description: string | null;
  host_id: string;
  created_at: string;
};
export type MeetingDetail = Meeting & {
  host: User;
  participants: Array<{
    user_id: string;
    role: string;
    joined_at: string;
    user: User;
  }>;
  transcripts: Array<{
    id: string;
    transcript_text: string;
    cleaned_transcript?: string | null;
    summary?: string | null;
    key_points: string[];
    action_items: ActionItem[];
    segment_index: number | null;
    created_at: string;
  }>;
};

export const authApi = {
  register: (body: {
    email: string;
    password: string;
    full_name?: string | null;
  }) =>
    apiRequest<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    apiRequest<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const meetingsApi = {
  create: (
    token: string,
    body: { title: string; description?: string | null }
  ) =>
    apiRequest<Meeting>("/api/v1/meetings", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
  join: (token: string, meetingId: string) =>
    apiRequest<Meeting>(`/api/v1/meetings/${meetingId}/join`, {
      method: "POST",
      token,
    }),
  get: (token: string, meetingId: string) =>
    apiRequest<MeetingDetail>(`/api/v1/meetings/${meetingId}`, { token }),
  ask: (token: string, meetingId: string, question: string) =>
    apiRequest<MeetingQuestionResult>(`/api/v1/meetings/${meetingId}/ask`, {
      method: "POST",
      token,
      body: JSON.stringify({ question }),
    }),

  /** Multipart upload — Whisper transcription + Groq summary on the server. */
  uploadAudio: (token: string, meetingId: string, file: File) =>
    uploadMeetingAudio(token, meetingId, file),
};

export const transcriptsApi = {
  update: (token: string, transcriptId: string, cleanedTranscript: string) =>
    apiRequest<TranscriptUpdateResult>(`/api/v1/transcripts/${transcriptId}`, {
      method: "PUT",
      token,
      body: JSON.stringify({ cleaned_transcript: cleanedTranscript }),
    }),
  regenerate: (token: string, transcriptId: string) =>
    apiRequest<TranscriptRegenerateResult>(
      `/api/v1/transcripts/${transcriptId}/regenerate`,
      {
        method: "POST",
        token,
      }
    ),
};

export type AudioUploadResult = {
  transcript: string;
  cleaned_transcript: string;
  summary: string;
  key_points: string[];
  action_items: ActionItem[];
};

export type MeetingQuestionResult = {
  answer: string;
};

export type TranscriptUpdateResult = {
  message: string;
};

export type TranscriptRegenerateResult = {
  id: string;
  transcript_text: string;
  cleaned_transcript?: string | null;
  summary?: string | null;
  key_points: string[];
  action_items: ActionItem[];
  segment_index: number | null;
  created_at: string;
};

async function uploadMeetingAudio(
  token: string,
  meetingId: string,
  file: File
): Promise<AudioUploadResult> {
  const form = new FormData();
  form.append("file", file);
  const url = `${API_BASE}/api/v1/meetings/${meetingId}/upload-audio`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
  } catch (e) {
    const isNetwork =
      e instanceof TypeError &&
      (e.message === "Failed to fetch" || e.message === "Load failed");
    const hint = isNetwork
      ? ` Cannot reach ${API_BASE}. Start the backend: cd backend && .\\run-api.ps1`
      : "";
    const message =
      e instanceof Error ? `${e.message}.${hint}` : `Network error.${hint}`;
    throw new ApiError(message.trim(), 0);
  }
  const data = await parseJson<AudioUploadResult & { detail?: unknown }>(res);
  if (!res.ok) {
    const detail = formatErrorDetail(data, res.statusText);
    throw new ApiError(detail || "Upload failed", res.status, data);
  }
  return data as AudioUploadResult;
}
