"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import {
  fetchQuotaMetrics,
  fetchUpgradeCandidates,
  QuotaMetrics,
  QuotaSeriesPoint,
  UpgradeCandidate,
} from "../../../lib/adminAnalytics";

function SkeletonCard({ height = "200px" }: { height?: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-900/60 animate-pulse" style={{ height }} />;
}

export default function AdminQuotaAnalytics() {
  const [metrics, setMetrics] = useState<QuotaMetrics | null>(null);
  const [candidates, setCandidates] = useState<UpgradeCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, c] = await Promise.all([fetchQuotaMetrics(), fetchUpgradeCandidates(7, 50)]);
      setMetrics(m);
      setCandidates(c.items || []);
    } catch (e: any) {
      setError(e.message || "Failed to load quota analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const series: QuotaSeriesPoint[] = useMemo(() => metrics?.series_7d || [], [metrics]);
  const emptySeries = !loading && (!metrics || series.length === 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <CardTitle className="text-xl">Quota funnel</CardTitle>
        <Button variant="ghost" onClick={load} disabled={loading}>
          Refresh
        </Button>
      </div>

      {error && <div className="text-red-400 text-sm">Error: {error}</div>}

      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase text-slate-400">Quota hits (today)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.today.quota_exceeded_events ?? 0}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase text-slate-400">Users hit quota (today)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.today.users_hit_quota ?? 0}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase text-slate-400">Quota hits (7d)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.last_7d.quota_exceeded_events ?? 0}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase text-slate-400">Users hit quota (7d)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.last_7d.users_hit_quota ?? 0}</CardContent>
          </Card>
        </div>
      )}

      {loading && (
        <div className="grid gap-4 md:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard height="300px" />
        </div>
      )}

      {!loading && emptySeries && (
        <Card>
          <CardContent className="py-6">
            <div className="text-slate-300 font-semibold">No quota hits yet.</div>
            <div className="text-slate-400 text-sm">Once users hit their daily limits, the funnel will appear here.</div>
          </CardContent>
        </Card>
      )}

      {!loading && !emptySeries && (
        <Card className="h-96">
          <CardHeader>
            <CardTitle>Quota hits over time (7d)</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="quota_exceeded_events" name="Quota hits" stroke="#f97316" />
                <Line type="monotone" dataKey="users_hit_quota" name="Users" stroke="#0ea5e9" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Upgrade candidates (last 7d)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <THead>
              <TR>
                <TH>Email</TH>
                <TH>Plan</TH>
                <TH>Quota hits</TH>
                <TH>Total searches</TH>
                <TH>Last hit</TH>
              </TR>
            </THead>
            <TBody>
              {candidates.map((c) => (
                <TR key={c.user_id}>
                  <TD>{c.email || "unknown"}</TD>
                  <TD>{c.plan?.name || "unknown"}</TD>
                  <TD>{c.quota_exceeded_count}</TD>
                  <TD>{c.total_searches}</TD>
                  <TD>{c.last_quota_hit_at ? new Date(c.last_quota_hit_at).toLocaleString() : "-"}</TD>
                </TR>
              ))}
              {candidates.length === 0 && (
                <TR>
                  <TD colSpan={5} className="text-slate-500 text-sm py-4 text-center">
                    No upgrade candidates yet.
                  </TD>
                </TR>
              )}
            </TBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
