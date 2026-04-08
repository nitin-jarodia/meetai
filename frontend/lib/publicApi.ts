/**
 * Single source of truth for the backend URL in the browser.
 * NEXT_PUBLIC_* is inlined at build time; defaults match backend/README.
 */

export function getPublicApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return raw.replace(/\/+$/, "");
}

/** WebSocket origin: http→ws, https→wss (matches API host/port). */
export function getWebSocketBaseUrl(): string {
  const httpBase = getPublicApiBaseUrl();
  if (httpBase.startsWith("https://")) {
    return `wss://${httpBase.slice("https://".length)}`;
  }
  if (httpBase.startsWith("http://")) {
    return `ws://${httpBase.slice("http://".length)}`;
  }
  return httpBase;
}
