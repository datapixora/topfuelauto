"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { API_BASE, authHeaders } from "../../lib/api";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { cn } from "../../lib/utils";

type Overview = {
  total_users: number;
  admins: number;
  searches_today: number;
  mrr: number;
  active_subscriptions: number;
  new_signups: number;
  provider_health: any[];
};

export default function AdminDashboard() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/metrics/overview`, {
          credentials: "include",
          headers: { ...authHeaders() },
        });
        if (!res.ok) throw new Error("Failed to load metrics");
        const json = await res.json();
        setOverview(json);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, []);

  const kpis = [
    { label: "Active users", value: overview?.total_users ?? "—" },
    { label: "Admins", value: overview?.admins ?? "—" },
    { label: "New signups", value: overview?.new_signups ?? "—" },
    { label: "MRR", value: overview?.mrr ?? "—" },
    { label: "Active subs", value: overview?.active_subscriptions ?? "—" },
    { label: "Searches today", value: overview?.searches_today ?? "—" },
  ];

  const userSeries = [
    { day: "Mon", signups: 12, active: 40 },
    { day: "Tue", signups: 18, active: 42 },
    { day: "Wed", signups: 14, active: 45 },
    { day: "Thu", signups: 21, active: 47 },
    { day: "Fri", signups: 19, active: 49 },
  ];

  const planSeries = [
    { name: "Free", value: 1200 },
    { name: "Pro", value: 340 },
    { name: "Ultimate", value: 28 },
  ];

  const searches = [
    { query: "Nissan GT-R 2005", count: 32 },
    { query: "Porsche 911", count: 20 },
    { query: "RS7", count: 12 },
  ];

  return (
    <div className="space-y-4">
      {error && <div className="text-red-400 text-sm">Error: {error}</div>}

      <div className="grid gap-3 md:grid-cols-3">
        {kpis.map((kpi) => (
          <Card key={kpi.label}>
            <CardHeader>
              <CardTitle className="text-sm text-slate-400">{kpi.label}</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{kpi.value}</CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="h-80">
          <CardHeader>
            <CardTitle>User growth</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={userSeries}>
                <defs>
                  <linearGradient id="colorSignup" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="day" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="signups" stroke="#0ea5e9" fill="url(#colorSignup)" />
                <Area type="monotone" dataKey="active" stroke="#22d3ee" fill="url(#colorActive)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="h-80">
          <CardHeader>
            <CardTitle>Subscriptions by plan</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={planSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Bar dataKey="value" fill="#0ea5e9" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Top searches</CardTitle>
          <Button variant="ghost" onClick={() => location.reload()}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {searches.map((s) => (
              <div key={s.query} className="flex justify-between text-sm">
                <span>{s.query}</span>
                <span className="text-slate-400">{s.count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
