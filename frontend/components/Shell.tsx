"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface ShellProps {
  title: string;
  children: React.ReactNode;
  sidebarUser?: string | null;
  sidebarFooter?: React.ReactNode;
}

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: "M4 5.5h7v7H4zM13 5.5h7v7h-7zM4 14.5h7v5H4zM13 14.5h7v5h-7z",
  },
  {
    label: "Meetings",
    href: "/dashboard",
    icon: "M7 3v3M17 3v3M4 8h16M5 6h14a1 1 0 0 1 1 1v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1Z",
  },
];

export function Shell({ title, children, sidebarUser, sidebarFooter }: ShellProps) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-background-base text-text-primary">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-background-border bg-background-surface md:flex md:flex-col">
        <div className="border-b border-background-border px-5 py-5">
          <Link href="/dashboard" className="flex items-center gap-2 text-2xl font-semibold">
            <span>MeetAI</span>
            <span className="text-brand-primary">●</span>
          </Link>
          <div className="mt-6 rounded-xl border border-background-border bg-background-elevated px-3 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Workspace</p>
            <p className="mt-2 truncate text-sm text-text-secondary">{sidebarUser || title}</p>
          </div>
        </div>
        <nav className="flex-1 space-y-2 px-4 py-5">
          {navItems.map((item) => {
            const active = item.label === "Meetings" ? pathname.startsWith("/meeting") : pathname.startsWith(item.href);
            return (
              <Link key={item.label} href={item.href} className={`flex h-9 items-center gap-3 rounded-md px-3 text-sm transition-all duration-150 ${active ? "bg-brand-primaryDim text-brand-primary" : "text-text-secondary hover:bg-background-elevated hover:text-text-primary"}`}>
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d={item.icon} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-background-border p-4">{sidebarFooter}</div>
      </aside>
      <main className="min-h-screen pb-20 md:pl-60 md:pb-0">
        <div className="mx-auto w-full max-w-7xl px-4 py-4 md:px-6 md:py-6">{children}</div>
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-background-border bg-background-surface/95 px-4 py-2 backdrop-blur md:hidden">
        {navItems.map((item) => {
          const active = item.label === "Meetings" ? pathname.startsWith("/meeting") : pathname.startsWith(item.href);
          return (
            <Link key={item.label} href={item.href} className={`flex flex-1 flex-col items-center gap-1 rounded-md px-3 py-2 text-xs ${active ? "text-brand-primary" : "text-text-secondary"}`}>
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7">
                <path d={item.icon} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
