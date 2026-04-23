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
  id?: string | null;
  task: string;
  assigned_to: string | null;
  deadline: string | null;
  due_at?: string | null;
  status?: string | null;
  assigned_user_id?: string | null;
  source?: string | null;
  updated_at?: string | null;
};

export type TranscriptSegment = {
  id: string;
  order_index: number;
  start_ms: number;
  end_ms: number;
  text: string;
  speaker_label: string;
  confidence: number | null;
};

export type TranscriptSegmentsResponse = {
  transcript_id: string;
  language: string | null;
  duration_ms: number | null;
  has_audio: boolean;
  segments: TranscriptSegment[];
};

export type TranscriptTranslation = {
  transcript_id: string;
  target_language: string;
  translated_text: string;
};

export type AskCitation = {
  meeting_id: string;
  meeting_title: string;
  transcript_id: string;
  chunk_index: number;
  score: number;
  snippet: string;
};

export type AskAcrossMeetingsResponse = {
  answer: string;
  citations: AskCitation[];
};
export type MeetingQAEntry = {
  id: string;
  transcript_id: string | null;
  question: string;
  answer: string;
  created_at: string;
  asked_by: User;
};
export type MeetingProcessingJob = {
  id: string;
  meeting_id: string;
  filename: string | null;
  status: string;
  stage: string;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  created_by: User;
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
    translated_text?: string | null;
    translated_language?: string | null;
    summary?: string | null;
    key_points: string[];
    action_items: ActionItem[];
    language?: string | null;
    duration_ms?: number | null;
    audio_path?: string | null;
    has_audio?: boolean;
    segment_index: number | null;
    created_at: string;
  }>;
  qa_history: MeetingQAEntry[];
  action_items: ActionItem[];
  processing_jobs: MeetingProcessingJob[];
};

export type MeetingTranscript = MeetingDetail["transcripts"][number];
export type MeetingListResult = { items: MeetingDetail[] };
export type MeetingSearchResult = {
  meeting: Meeting;
  score: number;
  snippet: string;
};
export type MeetingSearchResponse = {
  items: MeetingSearchResult[];
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
  list: (token: string, params?: { q?: string; limit?: number }) => {
    const search = new URLSearchParams();
    if (params?.q) search.set("q", params.q);
    if (params?.limit) search.set("limit", String(params.limit));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return apiRequest<MeetingListResult>(`/api/v1/meetings${suffix}`, { token });
  },
  search: (token: string, q: string, limit = 20) => {
    const search = new URLSearchParams({ q, limit: String(limit) });
    return apiRequest<MeetingSearchResponse>(
      `/api/v1/meetings/search?${search.toString()}`,
      { token }
    );
  },
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
  listJobs: (token: string, meetingId: string) =>
    apiRequest<MeetingProcessingJob[]>(`/api/v1/meetings/${meetingId}/jobs`, { token }),
  getJob: (token: string, jobId: string) =>
    apiRequest<MeetingProcessingJob>(`/api/v1/meetings/jobs/${jobId}`, { token }),
  exportNotes: (token: string, meetingId: string, format: "markdown" | "json") =>
    apiRequest<MeetingExportResult>(
      `/api/v1/meetings/${meetingId}/export?format=${format}`,
      { token }
    ),

  /** Multipart upload — queues background transcription + AI processing on the server. */
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
  segments: (token: string, transcriptId: string) =>
    apiRequest<TranscriptSegmentsResponse>(
      `/api/v1/transcripts/${transcriptId}/segments`,
      { token }
    ),
  translate: (token: string, transcriptId: string, target: string) =>
    apiRequest<TranscriptTranslation>(
      `/api/v1/transcripts/${transcriptId}/translate?target=${encodeURIComponent(target)}`,
      { method: "POST", token }
    ),
  audioUrl: (token: string, transcriptId: string) =>
    `${API_BASE}/api/v1/transcripts/${transcriptId}/audio?token=${encodeURIComponent(
      token
    )}`,
};

export const aiApi = {
  askAcrossMeetings: (
    token: string,
    body: { question: string; top_k?: number }
  ) =>
    apiRequest<AskAcrossMeetingsResponse>(`/api/v1/ai/ask`, {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
};

export const actionItemsApi = {
  update: (
    token: string,
    itemId: string,
    body: {
      task?: string | null;
      assigned_to_name?: string | null;
      assigned_user_id?: string | null;
      deadline?: string | null;
      due_at?: string | null;
      status?: string | null;
    }
  ) =>
    apiRequest<ActionItem>(`/api/v1/action-items/${itemId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(body),
    }),
};

export type AudioUploadResult = {
  job: MeetingProcessingJob;
};

export type MeetingQuestionResult = {
  answer: string;
  entry: MeetingQAEntry;
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

export type MeetingExportResult = {
  format: string;
  filename: string;
  content: string;
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
