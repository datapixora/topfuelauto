"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import TopNav from "../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { getQuota } from "../../../lib/api";

function SuccessContent() {
  const params = useSearchParams();
  const [message, setMessage] = useState("Payment successful — activating your plan...");
  const [quota, setQuota] = useState<string | null>(null);

  useEffect(() => {
    const sessionId = params.get("session_id");
    if (!sessionId) return;
    getQuota()
      .then((q) => {
        const plan = q.limit === null ? "Unlimited" : `${q.limit} searches/day`;
        setQuota(plan);
        setMessage("Your plan is active.");
      })
      .catch(() => setMessage("Payment completed. Your plan will activate shortly."));
  }, [params]);

  return (
    <div className="space-y-8">
      <TopNav />
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Payment successful</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-slate-200">
            <div>{message}</div>
            {quota && <div className="text-sm text-slate-400">Current quota: {quota}</div>}
            <div className="flex gap-3 pt-2">
              <Link
                href="/search"
                className="inline-flex flex-1 items-center justify-center rounded-md bg-brand-accent px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110"
              >
                Go to Search
              </Link>
              <Link href="/account/subscription" className="text-sm underline text-slate-100">
                View account
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function BillingSuccessPage() {
  return (
    <Suspense fallback={<div className="text-slate-400">Loading...</div>}>
      <SuccessContent />
    </Suspense>
  );
}
