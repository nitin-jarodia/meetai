"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.login({ email, password });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-enter flex min-h-screen items-center justify-center bg-background-base px-6 py-10">
      <Card className="w-full max-w-[400px] rounded-xl p-8">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-text-primary">MeetAI</h1>
          <span className="text-brand-primary">●</span>
        </div>
        <p className="mt-2 text-sm text-text-secondary">Sign in to your workspace</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <Input
            label="Email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
          <Input
            label="Password"
            type={showPassword ? "text" : "password"}
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            rightSlot={
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="text-text-secondary transition-colors hover:text-text-primary"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d={showPassword ? "M3 3l18 18M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2M9.88 5.09A10.94 10.94 0 0 1 12 4.5c5 0 9 3.5 10 7.5a10.66 10.66 0 0 1-3.07 4.57M6.1 6.1C4.15 7.47 2.77 9.48 2 12c1 4 5 7.5 10 7.5a10.4 10.4 0 0 0 4.23-.87" : "M2 12c1-4 5-7.5 10-7.5S21 8 22 12c-1 4-5 7.5-10 7.5S3 16 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            }
          />
          <Button type="submit" loading={loading} className="w-full">
            {loading ? "Signing in" : "Sign in"}
          </Button>
          {error ? (
            <p className="text-sm text-semantic-danger" role="alert">
              {error}
            </p>
          ) : null}
        </form>
        <p className="mt-6 text-center text-sm text-text-secondary">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-brand-primary underline underline-offset-4">
            Register
          </Link>
        </p>
      </Card>
    </main>
  );
}
