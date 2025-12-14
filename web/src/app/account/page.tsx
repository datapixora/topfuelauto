"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import TopNav from "../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { fetchAssistCards, getQuota } from "../../lib/api";
import { AssistCard, QuotaInfo } from "../../lib/types";
import { getToken } from "../../lib/auth";

export default function AccountPage() {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [cards, setCards] = useState<AssistCard[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    getQuota()
      .then((q) => setQuota(q))
      .catch(() => setQuota(null));
    fetchAssistCards()
      .then((res) => setCards(res.cards || []))
      .catch((e) => setError(e.message || "Failed to load assist cards"));
  }, []);

  return (
    <div className="space-y-8">
      <TopNav />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Plan & quota</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-200">
            {quota ? (
              <>
                <div>
                  Searches today:{" "}
                  {quota.limit === null ? "Unlimited" : `${quota.used ?? 0}/${quota.limit} (remaining ${quota.remaining ?? 0})`}
                </div>
                {quota.reset_at && <div className="text-xs text-slate-400">Resets at {new Date(quota.reset_at).toLocaleTimeString()}</div>}
              </>
            ) : (
              <div className="text-slate-400 text-sm">Sign in to see quota.</div>
            )}
            <Link href="/pricing" className="text-brand-accent text-sm underline">
              View plans
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>Assist</CardTitle>
            <Link href="/account/assist/new" className="text-sm text-brand-accent underline">
              New case
            </Link>
          </CardHeader>
          <CardContent className="space-y-2">
            {cards.length === 0 && <div className="text-slate-400 text-sm">No assist cases yet.</div>}
            {cards.map((c) => (
              <div key={c.id} className="flex items-center justify-between text-sm">
                <div>
                  <div className="font-semibold text-slate-100">{c.title}</div>
                  <div className="text-xs text-slate-400">
                    {c.mode} · {c.status} · {c.progress_percent}%{" "}
                    {c.next_run_at && `• next ${new Date(c.next_run_at).toLocaleString()}`}
                  </div>
                </div>
                <Link href={`/account/assist/${c.id}`} className="text-brand-accent text-xs underline">
                  View
                </Link>
              </div>
            ))}
            {error && <div className="text-red-400 text-xs">{error}</div>}
          </CardContent>
        </Card>
      </div>
      <div>
        <Link href="/account/assist" className="underline text-brand-accent text-sm">
          Go to Assist dashboard
        </Link>
      </div>
    </div>
  );
}
