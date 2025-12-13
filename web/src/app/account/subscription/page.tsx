"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, authHeaders } from "../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import JsonViewer from "../../components/JsonViewer";

export default function SubscriptionPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const run = async () => {
      if (!API_BASE) {
        setError("API base URL not set");
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/subscription/me`, { headers: { ...authHeaders() } });
        if (res.status === 401) {
          setError("Please login");
          router.push("/login");
          return;
        }
        if (!res.ok) throw new Error("Unable to load subscription");
        const json = await res.json();
        setData(json);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [router]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your Subscription</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {loading && <div className="text-slate-400">Loading...</div>}
        {error && !loading && <div className="text-red-400">{error}</div>}
        {data && (
          <>
            <div>Plan: {data.plan?.name} ({data.plan?.key})</div>
            <div>Status: {data.status}</div>
            <div>
              Quotas:
              <JsonViewer value={data.plan?.quotas || {}} />
            </div>
            <div>
              Features:
              <JsonViewer value={data.plan?.features || {}} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
