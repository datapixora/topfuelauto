"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../../components/ui/table";
import { Button } from "../../../../components/ui/button";
import { apiGet } from "../../../../lib/api";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type UserDetailResponse = {
  user: { id: number; email: string; is_active: boolean; is_admin: boolean; is_pro: boolean; created_at: string | null };
  plan: { id: number | null; name: string | null; searches_per_day: number | null };
  quota: { limit: number | null; used: number; remaining: number | null; reset_at: string | null };
  usage_7d: { date: string; search_count: number }[];
  recent_searches: { id: number; query: string | null; result_count: number | null; error_code: string | null; status: string | null; created_at: string | null }[];
  admin_actions: { action: string; payload: any; created_at: string | null; admin_user_id: number }[];
};

function Badge({ label, color }: { label: string; color: "green" | "red" | "blue" }) {
  const classes =
    color === "green"
      ? "bg-emerald-500/20 text-emerald-200"
      : color === "red"
        ? "bg-red-500/20 text-red-200"
        : "bg-sky-500/20 text-sky-200";
  return <span className={`rounded-full px-2 py-1 text-xs ${classes}`}>{label}</span>;
}

export default function AdminUserDetail() {
  const params = useParams();
  const userId = params?.id as string;
  const [data, setData] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<UserDetailResponse>(`/admin/users/${userId}/detail`);
      setData(res);
    } catch (e: any) {
      setError(e.message || "Failed to load user");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const usageSeries = useMemo(() => data?.usage_7d || [], [data]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-semibold">{data?.user.email || "User"}</div>
          <div className="text-sm text-slate-400">ID: {data?.user.id}</div>
        </div>
        <div className="flex gap-2">
          {data?.user.is_active ? <Badge label="Active" color="green" /> : <Badge label="Disabled" color="red" />}
          {data?.user.is_admin && <Badge label="Admin" color="blue" />}
          {data?.user.is_pro ? <Badge label="Pro plan" color="blue" /> : <Badge label="Free plan" color="green" />}
        </div>
      </div>

      {error && <div className="text-red-400 text-sm">Error: {error}</div>}
      {loading && <div className="text-slate-400 text-sm">Loading...</div>}

      {data && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Plan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-lg font-semibold">{data.plan.name || "Unknown"}</div>
                <div className="text-sm text-slate-400">
                  Searches/day: {data.plan.searches_per_day ?? "unlimited"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Quota today</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold">
                  {data.quota.limit === null ? "Unlimited" : `${data.quota.remaining ?? 0} remaining`}
                </div>
                {data.quota.limit !== null && (
                  <div className="text-xs text-slate-400">
                    Used {data.quota.used} / {data.quota.limit} {data.quota.reset_at ? `• Resets ${new Date(data.quota.reset_at).toLocaleTimeString()}` : ""}
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Created</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-slate-300">
                {data.user.created_at ? new Date(data.user.created_at).toLocaleString() : "-"}
              </CardContent>
            </Card>
          </div>

          <Card className="h-96">
            <CardHeader>
              <CardTitle>Usage (last 7d)</CardTitle>
            </CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={usageSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="search_count" name="Searches" stroke="#0ea5e9" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent searches</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <THead>
                  <TR>
                    <TH>When</TH>
                    <TH>Query</TH>
                    <TH>Results</TH>
                    <TH>Status</TH>
                  </TR>
                </THead>
                <TBody>
                  {data.recent_searches.map((s) => (
                    <TR key={s.id}>
                      <TD className="text-xs text-slate-400">{s.created_at ? new Date(s.created_at).toLocaleString() : "-"}</TD>
                      <TD>{s.query || "-"}</TD>
                      <TD>{s.result_count ?? "-"}</TD>
                      <TD className="text-xs">{s.error_code || s.status || "ok"}</TD>
                    </TR>
                  ))}
                  {data.recent_searches.length === 0 && (
                    <TR>
                      <TD colSpan={4} className="text-center text-slate-500 py-4">
                        No recent searches.
                      </TD>
                    </TR>
                  )}
                </TBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Admin actions</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <THead>
                  <TR>
                    <TH>When</TH>
                    <TH>Action</TH>
                    <TH>Payload</TH>
                    <TH>Admin</TH>
                  </TR>
                </THead>
                <TBody>
                  {data.admin_actions.map((a, idx) => (
                    <TR key={idx}>
                      <TD className="text-xs text-slate-400">{a.created_at ? new Date(a.created_at).toLocaleString() : "-"}</TD>
                      <TD>{a.action}</TD>
                      <TD className="text-xs text-slate-300">
                        {a.payload ? JSON.stringify(a.payload) : "-"}
                      </TD>
                      <TD>{a.admin_user_id}</TD>
                    </TR>
                  ))}
                  {data.admin_actions.length === 0 && (
                    <TR>
                      <TD colSpan={4} className="text-center text-slate-500 py-4">
                        No admin actions yet.
                      </TD>
                    </TR>
                  )}
                </TBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
