"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import TopNav from "../../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { AlertMatch, SavedSearchAlert } from "../../../../lib/types";
import { alertDetail, deleteAlert, updateAlert } from "../../../../lib/api";
import { useAuth } from "../../../../components/auth/AuthProvider";

export default function AlertDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading } = useAuth();
  const alertId = Number(params?.id);
  const [alertData, setAlertData] = useState<SavedSearchAlert | null>(null);
  const [matches, setMatches] = useState<AlertMatch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!alertId || Number.isNaN(alertId)) return;
    setLoadingState(true);
    setError(null);
    try {
      const res = await alertDetail(alertId);
      setAlertData(res.alert);
      setMatches(res.matches || []);
    } catch (e: any) {
      setError(e.message || "Failed to load alert");
    } finally {
      setLoadingState(false);
    }
  };

  useEffect(() => {
    if (!user && !loading) {
      router.replace(`/login?next=/account/alerts/${alertId}`);
      return;
    }
    if (user) void load();
  }, [user, loading, alertId]);

  const toggleActive = async () => {
    if (!alertData) return;
    setSaving(true);
    try {
      const updated = await updateAlert(alertData.id, { is_active: !alertData.is_active });
      setAlertData(updated);
    } catch (e: any) {
      setError(e.message || "Unable to update alert");
    } finally {
      setSaving(false);
    }
  };

  const destroy = async () => {
    if (!alertData) return;
    if (!confirm("Delete this alert?")) return;
    setSaving(true);
    try {
      await deleteAlert(alertData.id);
      router.replace("/account/alerts");
    } catch (e: any) {
      setError(e.message || "Unable to delete alert");
    } finally {
      setSaving(false);
    }
  };

  const fmt = (dt?: string | null) => (dt ? new Date(dt).toLocaleString() : "—");

  return (
    <div className="space-y-6">
      <TopNav />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-50">Alert detail</h1>
            {alertData && (
              <div className="text-sm text-slate-400">
              Next run {fmt(alertData.next_run_at)} • Last run {fmt(alertData.last_run_at)}
            </div>
          )}
        </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => router.push("/account/alerts")}>
              Back
            </Button>
            {alertData && (
              <>
                <Button
                  variant="ghost"
                  className="border border-slate-700"
                  onClick={toggleActive}
                  disabled={saving}
                >
                  {alertData.is_active ? "Pause" : "Resume"}
                </Button>
                <Button
                  variant="ghost"
                  className="border border-red-500/50 text-red-200 hover:bg-red-500/10"
                  onClick={destroy}
                  disabled={saving}
                >
                  Delete
                </Button>
              </>
            )}
          </div>
      </div>

      {error && <div className="rounded bg-red-500/10 border border-red-500/40 text-red-100 px-3 py-2 text-sm">{error}</div>}
      {loadingState && <div className="text-slate-400 text-sm">Loading...</div>}

      {alertData && (
        <Card className="border border-slate-800 bg-slate-900">
          <CardHeader>
            <CardTitle className="text-xl text-slate-50">{alertData.name || "Alert"}</CardTitle>
            <div className="text-xs text-slate-400">Cadence: {alertData.cadence_minutes ?? "?"} minutes</div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-200">
            <div className="text-xs text-slate-400">Query</div>
            <pre className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs overflow-auto">
              {JSON.stringify(alertData.query_json, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card className="border border-slate-800 bg-slate-900">
        <CardHeader>
          <CardTitle className="text-lg text-slate-50">Matches</CardTitle>
          <div className="text-xs text-slate-500">Newest first</div>
        </CardHeader>
        <CardContent className="space-y-2">
          {matches.length === 0 && <div className="text-slate-400 text-sm">No matches yet.</div>}
          {matches.map((m) => (
            <div
              key={m.id}
              className={`rounded border px-3 py-2 text-sm ${
                m.is_new ? "border-emerald-500/40 bg-emerald-500/5" : "border-slate-800 bg-slate-950"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="font-semibold text-slate-100">{m.title || m.listing_id}</div>
                <div className="text-xs text-slate-400">{fmt(m.matched_at)}</div>
              </div>
              <div className="text-xs text-slate-400">
                {m.location || "Location unknown"} {m.price ? `• $${m.price}` : ""}
              </div>
              {m.listing_url && (
                <Link href={m.listing_url} className="text-xs text-brand-accent underline" target="_blank">
                  View source
                </Link>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
