"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

export default function RegisterPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const strengthScore =
    Number(password.length >= 8) +
    Number(/[A-Z]/.test(password)) +
    Number(/[a-z]/.test(password) && /\d/.test(password)) +
    Number(/[^A-Za-z0-9]/.test(password));
  const strengthLabel =
    strengthScore >= 4 ? "Strong" : strengthScore >= 2 ? "Fair" : "Weak";
  const strengthTone =
    strengthScore >= 4
      ? "bg-semantic-success"
      : strengthScore >= 2
        ? "bg-semantic-warning"
        : "bg-semantic-danger";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await authApi.register({
        email,
        password,
        full_name: fullName || null,
      });
      const login = await authApi.login({ email, password });
      setToken(login.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Registration failed"
      );
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
        <p className="mt-2 text-sm text-text-secondary">Create your workspace account</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
          <Input label="Email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
          <div className="space-y-2">
            <Input
              label="Password"
              type={showPassword ? "text" : "password"}
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              hint="Use at least 8 characters."
              rightSlot={
                <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="text-text-secondary hover:text-text-primary" aria-label={showPassword ? "Hide password" : "Show password"}>
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d={showPassword ? "M3 3l18 18M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2M9.88 5.09A10.94 10.94 0 0 1 12 4.5c5 0 9 3.5 10 7.5a10.66 10.66 0 0 1-3.07 4.57M6.1 6.1C4.15 7.47 2.77 9.48 2 12c1 4 5 7.5 10 7.5a10.4 10.4 0 0 0 4.23-.87" : "M2 12c1-4 5-7.5 10-7.5S21 8 22 12c-1 4-5 7.5-10 7.5S3 16 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"} strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
              }
            />
            <div className="space-y-1">
              <div className="h-2 overflow-hidden rounded-full bg-background-elevated">
                <div className={`h-full rounded-full transition-all duration-150 ${strengthTone}`} style={{ width: `${Math.max(20, strengthScore * 25)}%` }} />
              </div>
              <p className="text-xs text-text-secondary">Strength: {password ? strengthLabel : "Weak"}</p>
            </div>
          </div>
          <Input
            label="Confirm password"
            type={showConfirmPassword ? "text" : "password"}
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={confirmPassword && confirmPassword !== password ? "Passwords must match" : null}
            rightSlot={
              <button type="button" onClick={() => setShowConfirmPassword((prev) => !prev)} className="text-text-secondary hover:text-text-primary" aria-label={showConfirmPassword ? "Hide password" : "Show password"}>
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8"><path d={showConfirmPassword ? "M3 3l18 18M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2M9.88 5.09A10.94 10.94 0 0 1 12 4.5c5 0 9 3.5 10 7.5a10.66 10.66 0 0 1-3.07 4.57M6.1 6.1C4.15 7.47 2.77 9.48 2 12c1 4 5 7.5 10 7.5a10.4 10.4 0 0 0 4.23-.87" : "M2 12c1-4 5-7.5 10-7.5S21 8 22 12c-1 4-5 7.5-10 7.5S3 16 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"} strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            }
          />
          <Button type="submit" loading={loading} className="w-full">
            {loading ? "Creating account" : "Create account"}
          </Button>
          {error ? (
            <p className="text-sm text-semantic-danger" role="alert">
              {error}
            </p>
          ) : null}
        </form>
        <p className="mt-6 text-center text-sm text-text-secondary">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-primary underline underline-offset-4">
            Log in
          </Link>
        </p>
      </Card>
    </main>
  );
}
