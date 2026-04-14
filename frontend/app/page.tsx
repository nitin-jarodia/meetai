import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function HomePage() {
  return (
    <main className="page-enter flex min-h-screen items-center justify-center bg-background-base px-6 py-10">
      <Card className="w-full max-w-2xl rounded-xl p-10 text-center">
        <div className="mx-auto flex w-fit items-center gap-2 text-4xl font-semibold">
          <span>MeetAI</span>
          <span className="text-brand-primary">●</span>
        </div>
        <p className="mx-auto mt-4 max-w-xl text-base text-text-secondary">
          A meeting workspace for transcription, summaries, action items, and follow-up
          answers in one clean dashboard.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/login">
            <Button>Log in</Button>
          </Link>
          <Link href="/register">
            <Button variant="ghost">Register</Button>
          </Link>
        </div>
      </Card>
    </main>
  );
}
