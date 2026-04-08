import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MeetAI",
  description: "AI Meeting Assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
