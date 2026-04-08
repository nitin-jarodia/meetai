import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold text-slate-900">MeetAI</h1>
      <p className="max-w-md text-center text-slate-600">
        Scalable AI meeting assistant foundation — sign in to open your dashboard.
      </p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="rounded-lg bg-brand-600 px-5 py-2.5 text-white hover:bg-brand-700"
        >
          Log in
        </Link>
        <Link
          href="/register"
          className="rounded-lg border border-slate-300 px-5 py-2.5 text-slate-800 hover:bg-slate-100"
        >
          Register
        </Link>
      </div>
    </main>
  );
}
