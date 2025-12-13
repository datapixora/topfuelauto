import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TopFuel Auto",
  description: "Search-first vehicle marketplace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <header className="flex items-center justify-between mb-8">
            <div className="text-2xl font-bold">TopFuel Auto</div>
            <div className="text-sm text-slate-400">Search smarter. Buy better.</div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}