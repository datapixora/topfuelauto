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
  BarChart,
  Bar,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import {
  fetchSearchAnalytics,
  ProviderStats,
  SearchAnalyticsResponse,
  SearchSeriesPoint,
  TopQuery,
  ZeroQuery,
} from "../../../lib/adminAnalytics";

const ranges = ["24h", "7d", "30d", "90d"];

function SkeletonCard({ height = "200px" }: { height?: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-900/60 animate-pulse" style={{ height }} />;
}

export default function AdminSearchAnalytics() {
  const [range, setRange] = useState<string>("7d");
  const [data, setData] = useState<SearchAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (selectedRange: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSearchAnalytics(selectedRange);
      setData(res);
    } catch (e: any) {
      setError(e.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(range);
  }, [range]);

  const series: SearchSeriesPoint[] = data?.series || [];
  const topQueries: TopQuery[] = data?.top_queries || [];
  const zeroQueries: ZeroQuery[] = data?.zero_queries || [];
  const providers: ProviderStats[] = data?.providers || [];

  const empty = !loading && (!data || (series.length === 0 && topQueries.length === 0 && zeroQueries.length === 0));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <CardTitle className="text-xl">Search analytics</CardTitle>
        <div className="flex gap-2">
          {ranges.map((r) => (
            <Button key={r} variant={r === range ? "primary" : "ghost"} onClick={() => setRange(r)}>
              {r}
            </Button>
          ))}
        </div>
      </div>

      {error && <div className="text-red-400 text-sm">Error: {error}</div>}

      {loading && (
        <div className="grid gap-4 md:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard height="140px" />
        </div>
      )}

      {!loading && empty && (
        <Card>
          <CardContent className="py-6">
            <div className="text-slate-300 font-semibold">No search data yet.</div>
            <div className="text-slate-400 text-sm">Run a search on the main site to start seeing analytics.</div>
          </CardContent>
        </Card>
      )}

      {!loading && !empty && (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="h-80">
              <CardHeader>
                <CardTitle>Searches over time</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="bucket" tickFormatter={(v) => v?.slice(5, 10)} stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="searches" stroke="#0ea5e9" />
                    <Line type="monotone" dataKey="zero_results" stroke="#f97316" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="h-80">
              <CardHeader>
                <CardTitle>Errors over time</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="bucket" tickFormatter={(v) => v?.slice(5, 10)} stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="errors" stroke="#ef4444" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top queries</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <THead>
                    <TR>
                      <TH>Query</TH>
                      <TH>Count</TH>
                      <TH>Zero %</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {topQueries.map((t, idx) => {
                      const zeroRate = t.count ? Math.round((t.zero_count / t.count) * 100) : 0;
                      return (
                        <TR key={idx}>
                          <TD>{t.query || "—"}</TD>
                          <TD>{t.count}</TD>
                          <TD>{zeroRate}%</TD>
                        </TR>
                      );
                    })}
                    {topQueries.length === 0 && (
                      <TR>
                        <TD colSpan={3} className="text-slate-500 text-sm py-4 text-center">
                          No queries yet.
                        </TD>
                      </TR>
                    )}
                  </TBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Zero-result queries</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <THead>
                    <TR>
                      <TH>Query</TH>
                      <TH>Zero count</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {zeroQueries.map((z, idx) => (
                      <TR key={idx}>
                        <TD>{z.query || "—"}</TD>
                        <TD>{z.count}</TD>
                      </TR>
                    ))}
                    {zeroQueries.length === 0 && (
                      <TR>
                        <TD colSpan={2} className="text-slate-500 text-sm py-4 text-center">
                          No zero-result searches.
                        </TD>
                      </TR>
                    )}
                  </TBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Provider breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={providers}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="provider" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="count" name="Searches" fill="#0ea5e9" />
                      <Bar dataKey="error_count" name="Errors" fill="#ef4444" />
                      <Bar dataKey="cache_hits" name="Cache hits" fill="#22c55e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <Table>
                  <THead>
                    <TR>
                      <TH>Provider</TH>
                      <TH>Count</TH>
                      <TH>Error %</TH>
                      <TH>Cache hit %</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {providers.map((p, idx) => {
                      const errorRate = p.count ? Math.round((p.error_count / p.count) * 100) : 0;
                      const cacheRate = p.count ? Math.round((p.cache_hits / p.count) * 100) : 0;
                      return (
                        <TR key={idx}>
                          <TD>{p.provider}</TD>
                          <TD>{p.count}</TD>
                          <TD>{errorRate}%</TD>
                          <TD>{cacheRate}%</TD>
                        </TR>
                      );
                    })}
                    {providers.length === 0 && (
                      <TR>
                        <TD colSpan={4} className="text-slate-500 text-sm py-4 text-center">
                          No provider data yet.
                        </TD>
                      </TR>
                    )}
                  </TBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
