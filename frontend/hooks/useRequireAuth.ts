"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";

/**
 * Redirect to /login if no JWT (client-side guard).
 * Waits for zustand persist to rehydrate from localStorage so we do not
 * redirect before the token is restored.
 */
export function useRequireAuth() {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const [rehydrated, setRehydrated] = useState(false);

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) {
      setRehydrated(true);
      return;
    }
    const unsub = useAuthStore.persist.onFinishHydration(() => {
      setRehydrated(true);
    });
    return unsub;
  }, []);

  useEffect(() => {
    if (!rehydrated) return;
    if (!token) {
      router.replace("/login");
    }
  }, [rehydrated, token, router]);

  if (!rehydrated) {
    return undefined;
  }
  return token;
}
