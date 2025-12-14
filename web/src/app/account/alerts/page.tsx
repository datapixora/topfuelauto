"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import TopNav from "../../../components/TopNav";
import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { SavedSearchAlert } from "../../../lib/types";
import { deleteAlert, listAlerts, updateAlert } from "../../../lib/api";
import { useAuth } from "../../../components/auth/AuthProvider";

const fmt = (dt?: string | null) => (dt ? new Date(dt).toLocaleString() : "—");

export default function AlertsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [alerts, setAlerts] = useState<SavedSearchAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  const load = async () => {
    if (!user) return;
    setError(null);
    try {
      const res = await listAlerts();
      setAlerts(res);
    } catch (e: any) {
      setError(e.message || "Failed to load alerts");
    }
  };

  useEffect(() => {
    if (!user && !loading) {
      router.replace("/login?next=/account/alerts");
      return;
    }
    if (user) void load();
  }, [user, loading]);

  const toggleActive = async (alert: SavedSearchAlert) => {
    setSavingId(alert.id);
    try {
      await updateAlert(alert.id, { is_active: !alert.is_active });
      await load();
    } catch (e: any) {
      setError(e.message || "Unable to update alert");
    } finally {
      setSavingId(null);
    }
  };

  const destroy = async (alert: SavedSearchAlert) => {
    if (!confirm("Delete this alert?")) return;
    setSavingId(alert.id);
    try {
      await deleteAlert(alert.id);
      await load();
    } catch (e: any) {
      setError(e.message || "Unable to delete alert");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <TopNav />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-50">Saved alerts</h1>
          <p className="text-slate-400 text-sm">We will run these searches on a schedule and notify you of new matches.</p>
        </div>
        <Button onClick={() => router.push("/account/alerts/new")}>New alert</Button>
      </div>

      {error && <div className="rounded bg-red-500/10 border border-red-500/40 text-red-100 px-3 py-2 text-sm">{error}</div>}

      <div className="grid gap-4 md:grid-cols-2">
        {alerts.length === 0 && (
          <Card className="border border-slate-800 bg-slate-900">
            <CardContent className="py-6 text-slate-400 text-sm">No alerts yet. Create one to get notified on new matches.</CardContent>
          </Card>
        )}
        {alerts.map((alert) => (
          <Card key={alert.id} className="border border-slate-800 bg-slate-900">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg text-slate-50">{alert.name || "Alert"}</CardTitle>
                <div className="text-xs text-slate-500">Every {alert.cadence_minutes ?? "?"} minutes</div>
              </div>
              <span
                className={`rounded-full px-2 py-1 text-xs ${
                  alert.is_active ? "bg-emerald-500/20 text-emerald-200" : "bg-slate-800 text-slate-300"
                }`}
              >
                {alert.is_active ? "Active" : "Paused"}
              </span>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-200">
              <div className="text-xs text-slate-400">Next run: {fmt(alert.next_run_at)}</div>
              <div className="text-xs text-slate-400">Last run: {fmt(alert.last_run_at)}</div>
              <div className="flex gap-2">
                <Link href={`/account/alerts/${alert.id}`} className="text-brand-accent underline text-sm">
                  View
                </Link>
                <button
                  className="text-sm underline text-slate-300"
                  onClick={() => toggleActive(alert)}
                  disabled={savingId === alert.id}
                >
                  {alert.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  className="text-sm underline text-red-300"
                  onClick={() => destroy(alert)}
                  disabled={savingId === alert.id}
                >
                  Delete
                </button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
