"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TopNav from "../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { listAssistCases } from "../../../lib/api";
import { useAuth } from "../../../components/auth/AuthProvider";

export default function AssistListPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [cases, setCases] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user && !loading) {
      router.replace("/login?next=/account/assist");
      return;
    }
    if (!user) return;
    listAssistCases()
      .then((res) => setCases(res.cases || []))
      .catch((e) => setError(e.message || "Failed to load cases"));
  }, [user, loading, router]);

  return (
    <div className="space-y-6">
      <TopNav />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Assist cases</h1>
          <p className="text-slate-400 text-sm">Track your AI assist requests.</p>
        </div>
        <Link href="/account/assist/new" className="text-sm text-brand-accent underline">
          New case
        </Link>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}

      <div className="grid gap-3">
        {cases.map((c) => (
          <Card key={c.id}>
            <CardHeader className="flex items-center justify-between">
              <CardTitle className="text-base">{c.title || "Untitled"}</CardTitle>
              <span className="text-xs text-slate-400">
                {c.mode} • {c.status}
              </span>
            </CardHeader>
            <CardContent className="flex items-center justify-between text-sm text-slate-300">
              <div>Last run: {c.last_run_at ? new Date(c.last_run_at).toLocaleString() : "-"}</div>
              <Link href={`/account/assist/${c.id}`} className="text-brand-accent underline text-xs">
                View
              </Link>
            </CardContent>
          </Card>
        ))}
        {cases.length === 0 && <div className="text-slate-400 text-sm">No cases yet.</div>}
      </div>
    </div>
  );
}
