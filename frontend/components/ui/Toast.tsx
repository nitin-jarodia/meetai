"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface ToastItem { id: number; message: string; variant: "success" | "error" | "info"; }
interface ToastContextValue { showToast: (message: string, variant?: ToastItem["variant"]) => void; }
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const value = useMemo<ToastContextValue>(() => ({
    showToast: (message, variant = "info") => {
      const id = Date.now() + Math.random();
      setItems((prev) => [...prev, { id, message, variant }]);
      window.setTimeout(() => setItems((prev) => prev.filter((item) => item.id !== id)), 4000);
    },
  }), []);
  const tone = { success: "border-semantic-success/30 bg-semantic-success/15 text-semantic-success", error: "border-semantic-danger/30 bg-semantic-danger/15 text-semantic-danger", info: "border-semantic-info/30 bg-semantic-info/15 text-semantic-info" };
  return (
    <ToastContext.Provider value={value}>
      {children}
      {typeof document !== "undefined" ? createPortal(
        <div className="fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-3 px-4">
          {items.map((item) => <div key={item.id} className={`translate-x-0 rounded-xl border px-4 py-3 text-sm shadow-card transition-all duration-250 ${tone[item.variant]}`}>{item.message}</div>)}
        </div>,
        document.body
      ) : null}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used within ToastProvider");
  return value;
}
