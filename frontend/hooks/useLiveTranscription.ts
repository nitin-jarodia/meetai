"use client";

import { useEffect, useRef, useState } from "react";

type TranscriptDeltaEvent = {
  type: "transcript_delta";
  text: string;
  user_id: string;
};

export function useLiveTranscription(socket: WebSocket | null) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!socket) return;

    const handleMessage = (event: MessageEvent) => {
      if (typeof event.data !== "string") {
        return;
      }
      try {
        const payload = JSON.parse(event.data) as TranscriptDeltaEvent | { type: string };
        if (payload.type === "transcript_delta" && "text" in payload) {
          const nextText = payload.text.trim();
          if (!nextText) return;
          setTranscript((prev) => (prev ? `${prev} ${nextText}` : nextText));
        }
      } catch {
        /* ignore non-json messages */
      }
    };

    socket.addEventListener("message", handleMessage);
    return () => {
      socket.removeEventListener("message", handleMessage);
    };
  }, [socket]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      for (const track of streamRef.current?.getTracks() ?? []) {
        track.stop();
      }
    };
  }, []);

  async function startRecording(): Promise<void> {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("Live transcription socket is not connected.");
      return;
    }
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      typeof MediaRecorder === "undefined"
    ) {
      setError("This browser does not support live audio recording.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          socket.send(event.data);
        }
      };
      recorder.onerror = () => {
        setError("Recording failed. Please try again.");
      };
      recorder.start(3000);
      setError(null);
      setIsRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not access microphone.");
    }
  }

  function stopRecording(): void {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    for (const track of streamRef.current?.getTracks() ?? []) {
      track.stop();
    }
    streamRef.current = null;
    mediaRecorderRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));
    }
    setIsRecording(false);
  }

  return { isRecording, transcript, error, startRecording, stopRecording };
}
