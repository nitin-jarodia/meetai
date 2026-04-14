"use client";

import { useEffect, useRef, useState } from "react";
import { getWebSocketBaseUrl } from "@/lib/publicApi";

export type MeetingSocketEvent =
  | { type: "connected"; meeting_id: string; authenticated: boolean }
  | { type: "job_updated"; job: Record<string, unknown> }
  | { type: "transcript_ready"; meeting_id: string; job_id: string }
  | { type: "job_failed"; meeting_id: string; job_id: string; error: string }
  | { type: "pong" }
  | { type: "ack"; payload: string };

export function useMeetingSocket(
  meetingId: string,
  token: string | undefined,
  onEvent: (event: MeetingSocketEvent) => void
) {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!meetingId || !token) return;

    const wsBase = getWebSocketBaseUrl();
    const socket = new WebSocket(
      `${wsBase}/ws/meetings/${meetingId}?token=${encodeURIComponent(token)}`
    );

    socket.onopen = () => {
      setConnected(true);
    };

    socket.onclose = () => {
      setConnected(false);
    };

    socket.onerror = () => {
      setConnected(false);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as MeetingSocketEvent;
        onEventRef.current(payload);
      } catch {
        /* ignore malformed messages */
      }
    };

    const heartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 15000);

    return () => {
      window.clearInterval(heartbeat);
      socket.close();
    };
  }, [meetingId, token]);

  return { connected };
}
