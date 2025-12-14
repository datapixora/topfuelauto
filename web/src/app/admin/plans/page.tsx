"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, authHeaders } from "../../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import JsonViewer from "../../../components/JsonViewer";

type Plan = {
  id: number;
  key: string;
  name: string;
  price_monthly: number | null;
  description?: string | null;
  features?: Record<string, any> | null;
  quotas?: Record<string, any> | null;
  is_active: boolean;
  stripe_price_id_monthly?: string | null;
  stripe_price_id_yearly?: string | null;
  searches_per_day?: number | null;
  quota_reached_message?: string | null;
  assist_one_shot_per_day?: number | null;
  assist_watch_enabled?: boolean | null;
  assist_watch_max_cases?: number | null;
  assist_watch_runs_per_day?: number | null;
  assist_ai_budget_cents_per_day?: number | null;
  assist_reruns_per_day?: number | null;
  alerts_enabled?: boolean | null;
  alerts_max_active?: number | null;
  alerts_cadence_minutes?: number | null;
};

const FEATURE_LABELS: Record<string, string> = {
  vin_history: "VIN history access",
  priority_support: "Priority support",
  bulk: "Bulk tools",
  vin_decode: "VIN decode",
};

const QUOTA_LABELS: Record<string, string> = {
  searches_per_day: "Searches per day",
  alerts_max: "Saved alerts",
  vin_lookups_per_month: "VIN lookups / month",
};

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl max-w-2xl w-full relative">
        <button className="absolute right-3 top-3 text-slate-400" onClick={onClose}>
          x
        </button>
        {children}
      </div>
    </div>
  );
}

export default function AdminPlans() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    price: "",
    features: "{}",
    quotas: "{}",
    searches_per_day: "",
    quota_reached_message: "",
    stripe_price_id_monthly: "",
    stripe_price_id_yearly: "",
    assist_one_shot_per_day: "",
    assist_watch_enabled: false,
    assist_watch_max_cases: "",
    assist_watch_runs_per_day: "",
    assist_ai_budget_cents_per_day: "",
    assist_reruns_per_day: "",
    alerts_enabled: false,
    alerts_max_active: "",
    alerts_cadence_minutes: "",
  });
  const [parseError, setParseError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState<Record<number, boolean>>({});

  const auth = useMemo(() => authHeaders(), []);

  useEffect(() => {
    if (!success) return;
    const t = setTimeout(() => setSuccess(null), 2500);
    return () => clearTimeout(t);
  }, [success]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/plans`, { headers: { ...auth } });
      if (!res.ok) throw new Error(`Failed to load plans (${res.status})`);
      const json = await res.json();
      setPlans(json.plans || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openEdit = (plan: Plan) => {
    setEditId(plan.id);
    setForm({
      name: plan.name || "",
      price: plan.price_monthly == null ? "" : String(plan.price_monthly),
      features: JSON.stringify(plan.features || {}, null, 2),
      quotas: JSON.stringify(plan.quotas || {}, null, 2),
      searches_per_day: plan.searches_per_day == null ? "" : String(plan.searches_per_day),
      quota_reached_message: plan.quota_reached_message || "",
      stripe_price_id_monthly: plan.stripe_price_id_monthly || "",
      stripe_price_id_yearly: plan.stripe_price_id_yearly || "",
      assist_one_shot_per_day: plan.assist_one_shot_per_day == null ? "" : String(plan.assist_one_shot_per_day),
      assist_watch_enabled: Boolean(plan.assist_watch_enabled),
      assist_watch_max_cases: plan.assist_watch_max_cases == null ? "" : String(plan.assist_watch_max_cases),
      assist_watch_runs_per_day: plan.assist_watch_runs_per_day == null ? "" : String(plan.assist_watch_runs_per_day),
      assist_ai_budget_cents_per_day:
        plan.assist_ai_budget_cents_per_day == null ? "" : String(plan.assist_ai_budget_cents_per_day),
      assist_reruns_per_day: plan.assist_reruns_per_day == null ? "" : String(plan.assist_reruns_per_day),
      alerts_enabled: Boolean(plan.alerts_enabled),
      alerts_max_active: plan.alerts_max_active == null ? "" : String(plan.alerts_max_active),
      alerts_cadence_minutes: plan.alerts_cadence_minutes == null ? "" : String(plan.alerts_cadence_minutes),
    });
    setParseError(null);
    setSuccess(null);
    setError(null);
  };

  const resetToCurrent = () => {
    if (editId === null) return;
    const plan = plans.find((p) => p.id === editId);
    if (!plan) return;
    setForm({
      name: plan.name || "",
      price: plan.price_monthly == null ? "" : String(plan.price_monthly),
      features: JSON.stringify(plan.features || {}, null, 2),
      quotas: JSON.stringify(plan.quotas || {}, null, 2),
      searches_per_day: plan.searches_per_day == null ? "" : String(plan.searches_per_day),
      quota_reached_message: plan.quota_reached_message || "",
      stripe_price_id_monthly: plan.stripe_price_id_monthly || "",
      stripe_price_id_yearly: plan.stripe_price_id_yearly || "",
      assist_one_shot_per_day: plan.assist_one_shot_per_day == null ? "" : String(plan.assist_one_shot_per_day),
      assist_watch_enabled: Boolean(plan.assist_watch_enabled),
      assist_watch_max_cases: plan.assist_watch_max_cases == null ? "" : String(plan.assist_watch_max_cases),
      assist_watch_runs_per_day: plan.assist_watch_runs_per_day == null ? "" : String(plan.assist_watch_runs_per_day),
      assist_ai_budget_cents_per_day:
        plan.assist_ai_budget_cents_per_day == null ? "" : String(plan.assist_ai_budget_cents_per_day),
      assist_reruns_per_day: plan.assist_reruns_per_day == null ? "" : String(plan.assist_reruns_per_day),
      alerts_enabled: Boolean(plan.alerts_enabled),
      alerts_max_active: plan.alerts_max_active == null ? "" : String(plan.alerts_max_active),
      alerts_cadence_minutes: plan.alerts_cadence_minutes == null ? "" : String(plan.alerts_cadence_minutes),
    });
    setParseError(null);
    setError(null);
  };

  const save = async () => {
    setParseError(null);
    let featuresObj: Record<string, any> | null = null;
    let quotasObj: Record<string, any> | null = null;
    try {
      featuresObj = form.features ? JSON.parse(form.features) : {};
      if (featuresObj !== null && typeof featuresObj !== "object") throw new Error();
    } catch (e: any) {
      setParseError("Features JSON invalid");
      return;
    }
    try {
      quotasObj = form.quotas ? JSON.parse(form.quotas) : {};
      if (quotasObj !== null && typeof quotasObj !== "object") throw new Error();
    } catch (e: any) {
      setParseError("Quotas JSON invalid");
      return;
    }
    const priceTrim = form.price.trim();
    const priceVal = priceTrim === "" ? null : Number(priceTrim);
    if (priceTrim !== "" && (!Number.isFinite(priceVal) || Number.isNaN(priceVal))) {
      setParseError("Price must be a number or blank");
      return;
    }
    const searchesTrim = form.searches_per_day.trim();
    const searchesVal = searchesTrim === "" ? null : Number(searchesTrim);
    if (searchesTrim !== "" && (!Number.isFinite(searchesVal) || Number.isNaN(searchesVal) || searchesVal < 0)) {
      setParseError("Searches per day must be a non-negative number or blank");
      return;
    }
    const assistOneShotTrim = form.assist_one_shot_per_day.toString().trim();
    const assistOneShotVal = assistOneShotTrim === "" ? null : Number(assistOneShotTrim);
    if (
      assistOneShotTrim !== "" &&
      (!Number.isFinite(assistOneShotVal) || Number.isNaN(assistOneShotVal) || assistOneShotVal < 0)
    ) {
      setParseError("Assist one-shot per day must be a non-negative number or blank");
      return;
    }

    const assistWatchMaxTrim = form.assist_watch_max_cases.toString().trim();
    const assistWatchMaxVal = assistWatchMaxTrim === "" ? null : Number(assistWatchMaxTrim);
    if (
      assistWatchMaxTrim !== "" &&
      (!Number.isFinite(assistWatchMaxVal) || Number.isNaN(assistWatchMaxVal) || assistWatchMaxVal < 0)
    ) {
      setParseError("Assist watch max cases must be a non-negative number or blank");
      return;
    }

    const assistWatchRunsTrim = form.assist_watch_runs_per_day.toString().trim();
    const assistWatchRunsVal = assistWatchRunsTrim === "" ? null : Number(assistWatchRunsTrim);
    if (
      assistWatchRunsTrim !== "" &&
      (!Number.isFinite(assistWatchRunsVal) || Number.isNaN(assistWatchRunsVal) || assistWatchRunsVal < 0)
    ) {
      setParseError("Assist watch runs per day must be a non-negative number or blank");
      return;
    }

    const assistBudgetTrim = form.assist_ai_budget_cents_per_day.toString().trim();
    const assistBudgetVal = assistBudgetTrim === "" ? null : Number(assistBudgetTrim);
    if (
      assistBudgetTrim !== "" &&
      (!Number.isFinite(assistBudgetVal) || Number.isNaN(assistBudgetVal) || assistBudgetVal < 0)
    ) {
      setParseError("Assist AI budget (cents per day) must be a non-negative number or blank");
      return;
    }

    const assistRerunsTrim = form.assist_reruns_per_day.toString().trim();
    const assistRerunsVal = assistRerunsTrim === "" ? null : Number(assistRerunsTrim);
    if (
      assistRerunsTrim !== "" &&
      (!Number.isFinite(assistRerunsVal) || Number.isNaN(assistRerunsVal) || assistRerunsVal < 0)
    ) {
      setParseError("Assist reruns per day must be a non-negative number or blank");
      return;
    }

    const alertsMaxTrim = form.alerts_max_active.toString().trim();
    const alertsMaxVal = alertsMaxTrim === "" ? null : Number(alertsMaxTrim);
    if (alertsMaxTrim !== "" && (!Number.isFinite(alertsMaxVal) || Number.isNaN(alertsMaxVal) || alertsMaxVal < 0)) {
      setParseError("Alerts max active must be a non-negative number or blank");
      return;
    }

    const alertsCadenceTrim = form.alerts_cadence_minutes.toString().trim();
    const alertsCadenceVal = alertsCadenceTrim === "" ? null : Number(alertsCadenceTrim);
    if (
      alertsCadenceTrim !== "" &&
      (!Number.isFinite(alertsCadenceVal) || Number.isNaN(alertsCadenceVal) || alertsCadenceVal < 0)
    ) {
      setParseError("Alerts cadence must be a non-negative number or blank");
      return;
    }
    const quotaMsg = form.quota_reached_message.trim();

    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/plans/${editId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...auth },
        body: JSON.stringify({
          name: form.name,
          price_monthly: priceVal,
          features: featuresObj,
          quotas: quotasObj,
          searches_per_day: searchesVal,
          quota_reached_message: quotaMsg === "" ? null : quotaMsg,
          stripe_price_id_monthly: form.stripe_price_id_monthly || null,
          stripe_price_id_yearly: form.stripe_price_id_yearly || null,
          assist_one_shot_per_day: assistOneShotVal,
          assist_watch_enabled: !!form.assist_watch_enabled,
          assist_watch_max_cases: assistWatchMaxVal,
          assist_watch_runs_per_day: assistWatchRunsVal,
          assist_ai_budget_cents_per_day: assistBudgetVal,
          assist_reruns_per_day: assistRerunsVal,
          alerts_enabled: !!form.alerts_enabled,
          alerts_max_active: alertsMaxVal,
          alerts_cadence_minutes: alertsCadenceVal,
        }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Save failed (${res.status}): ${txt}`);
      }
      setSuccess("Plan saved");
      await load();
      setEditId(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const priceDisplay = (plan: Plan) => {
    if (plan.price_monthly === null || plan.price_monthly === undefined) {
      return { price: "$0", badge: "Free" };
    }
    return { price: `$${plan.price_monthly}/mo`, badge: null };
  };

  const featureRows = (plan: Plan) => {
    const feats = plan.features || {};
    const known = Object.entries(FEATURE_LABELS).map(([key, label]) => ({
      key,
      label,
      enabled: Boolean((feats as any)?.[key]),
    }));
    const unknown = Object.entries(feats).filter(([k]) => !FEATURE_LABELS[k]);
    return { known, unknown };
  };

  const quotaRows = (plan: Plan) => {
    const qs = plan.quotas || {};
    const known = Object.entries(QUOTA_LABELS).map(([key, label]) => ({
      key,
      label,
      value: (qs as any)?.[key],
    }));
    const unknown = Object.entries(qs).filter(([k]) => !QUOTA_LABELS[k]);
    return { known, unknown };
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
          {success}
        </div>
      )}
      {loading && <div className="text-slate-400 text-sm">Loading...</div>}

      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const price = priceDisplay(plan);
          const { known: featureList, unknown: unknownFeatures } = featureRows(plan);
          const { known: quotaList, unknown: unknownQuotas } = quotaRows(plan);
          const showAdvanced = unknownFeatures.length > 0 || unknownQuotas.length > 0;
          const isAdvancedOpen = advancedOpen[plan.id] ?? false;

          return (
            <Card key={plan.id || plan.key} className="border border-slate-800 bg-slate-900">
              <CardHeader className="space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-xl text-slate-50">{plan.name}</CardTitle>
                    {plan.description && <div className="text-sm text-slate-400">{plan.description}</div>}
                  </div>
                  <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{plan.key}</span>
                </div>
                <div className="text-2xl font-semibold text-emerald-200">{price.price}</div>
                {price.badge && <div className="text-xs text-slate-400">{price.badge}</div>}
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Features</div>
                  <div className="mt-1 space-y-1">
                    {featureList.map((item) => (
                      <div key={item.key} className="flex items-center gap-2">
                        <span className={`text-lg ${item.enabled ? "text-emerald-400" : "text-slate-500"}`}>
                          {item.enabled ? "Yes" : "No"}
                        </span>
                        <span className="text-slate-200">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Quotas</div>
                  <div className="mt-1 space-y-1">
                    {quotaList.map((item) => (
                      <div key={item.key} className="flex items-center justify-between gap-2">
                        <span className="text-slate-200">{item.label}</span>
                        <span className="text-slate-100 font-mono">
                          {item.value === undefined || item.value === null ? "-" : item.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Usage limits</div>
                  <div className="mt-1 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-slate-200">Searches per day</span>
                      <span className="text-slate-100 font-mono">
                        {plan.searches_per_day === null || plan.searches_per_day === undefined
                          ? "-"
                          : plan.searches_per_day}
                      </span>
                    </div>
                    {plan.quota_reached_message && (
                      <div className="text-xs text-slate-400">
                        Message: <span className="text-slate-200">{plan.quota_reached_message}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Assist</div>
                  <div className="text-xs text-slate-400">Watch enabled: {plan.assist_watch_enabled ? "Yes" : "No"}</div>
                  <div className="text-xs text-slate-400">
                    One-shot/day: {plan.assist_one_shot_per_day ?? "-"} • Watch runs/day: {plan.assist_watch_runs_per_day ?? "-"}
                  </div>
                  <div className="text-xs text-slate-400">
                    Watch max cases: {plan.assist_watch_max_cases ?? "-"} • Reruns/day: {plan.assist_reruns_per_day ?? "-"}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Alerts</div>
                  <div className="text-xs text-slate-400">Enabled: {plan.alerts_enabled ? "Yes" : "No"}</div>
                  <div className="text-xs text-slate-400">
                    Max active: {plan.alerts_max_active ?? "-"} • Cadence: {plan.alerts_cadence_minutes ?? "-"} min
                  </div>
                </div>

                {showAdvanced && (
                  <div className="rounded border border-slate-800 bg-slate-950 px-3 py-2">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Advanced (JSON)</span>
                      <button
                        className="underline"
                        onClick={() => setAdvancedOpen({ ...advancedOpen, [plan.id]: !isAdvancedOpen })}
                      >
                        {isAdvancedOpen ? "Hide" : "Show"}
                      </button>
                    </div>
                    {isAdvancedOpen && (
                      <div className="mt-2 space-y-2 text-xs">
                        {unknownFeatures.length > 0 && (
                          <div>
                            <div className="text-slate-400">Other features</div>
                            <JsonViewer value={Object.fromEntries(unknownFeatures)} />
                          </div>
                        )}
                        {unknownQuotas.length > 0 && (
                          <div>
                            <div className="text-slate-400">Other quotas</div>
                            <JsonViewer value={Object.fromEntries(unknownQuotas)} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end">
                  <Button variant="ghost" onClick={() => openEdit(plan)}>
                    Edit
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {editId !== null && (
        <Modal onClose={() => setEditId(null)}>
          <div className="p-4 space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">Edit plan</div>
              <Button variant="ghost" onClick={resetToCurrent}>
                Reset to current
              </Button>
            </div>
            {parseError && <div className="rounded bg-red-500/10 px-2 py-1 text-red-200">{parseError}</div>}
            {error && <div className="rounded bg-red-500/10 px-2 py-1 text-red-200">{error}</div>}
            <label className="block space-y-1">
              <div className="text-slate-200">Name</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Price (monthly)</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="Leave blank for none/free"
              />
              <div className="text-xs text-slate-500">Numbers only; leave blank for free plans.</div>
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Searches per day (quota)</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.searches_per_day}
                onChange={(e) => setForm({ ...form, searches_per_day: e.target.value })}
                placeholder="Leave blank for unlimited"
              />
              <div className="text-xs text-slate-500">Must be a non-negative integer; leave blank for unlimited.</div>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={form.assist_watch_enabled}
                  onChange={(e) => setForm({ ...form, assist_watch_enabled: e.target.checked })}
                />
                <span>Assist watch enabled</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={form.alerts_enabled}
                  onChange={(e) => setForm({ ...form, alerts_enabled: e.target.checked })}
                />
                <span>Alerts enabled</span>
              </label>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Assist one-shot per day</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.assist_one_shot_per_day}
                  onChange={(e) => setForm({ ...form, assist_one_shot_per_day: e.target.value })}
                  placeholder="Leave blank for unlimited"
                />
              </label>
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Assist watch max cases</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.assist_watch_max_cases}
                  onChange={(e) => setForm({ ...form, assist_watch_max_cases: e.target.value })}
                  placeholder="Leave blank for unlimited"
                />
              </label>
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Assist watch runs per day</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.assist_watch_runs_per_day}
                  onChange={(e) => setForm({ ...form, assist_watch_runs_per_day: e.target.value })}
                  placeholder="Leave blank for unlimited"
                />
              </label>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Assist AI budget (cents/day)</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.assist_ai_budget_cents_per_day}
                  onChange={(e) => setForm({ ...form, assist_ai_budget_cents_per_day: e.target.value })}
                  placeholder="Leave blank for none"
                />
              </label>
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Assist reruns per day</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.assist_reruns_per_day}
                  onChange={(e) => setForm({ ...form, assist_reruns_per_day: e.target.value })}
                  placeholder="Leave blank for none"
                />
              </label>
              <label className="block space-y-1 text-sm text-slate-200">
                <div>Alerts max active</div>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                  value={form.alerts_max_active}
                  onChange={(e) => setForm({ ...form, alerts_max_active: e.target.value })}
                  placeholder="Leave blank for unlimited"
                />
              </label>
            </div>
            <label className="block space-y-1 text-sm text-slate-200">
              <div>Alerts cadence (minutes)</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.alerts_cadence_minutes}
                onChange={(e) => setForm({ ...form, alerts_cadence_minutes: e.target.value })}
                placeholder="Leave blank for plan default"
              />
              <div className="text-xs text-slate-500">Determines how often alerts run.</div>
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Features (JSON object)</div>
              <textarea
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 font-mono text-xs min-h-[120px]"
                value={form.features}
                onChange={(e) => setForm({ ...form, features: e.target.value })}
              />
              <div className="text-xs text-slate-500">Example: {'{ "vin_history": true }'}</div>
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Quotas (JSON object)</div>
              <textarea
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 font-mono text-xs min-h-[120px]"
                value={form.quotas}
                onChange={(e) => setForm({ ...form, quotas: e.target.value })}
              />
              <div className="text-xs text-slate-500">Example: {'{ "searches_per_day": 100 }'}</div>
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Quota reached message (optional)</div>
              <textarea
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
                value={form.quota_reached_message}
                onChange={(e) => setForm({ ...form, quota_reached_message: e.target.value })}
                placeholder="Daily search limit reached. Upgrade to continue."
                maxLength={2800}
              />
              <div className="text-xs text-slate-500">Shown to users when they hit the daily search limit.</div>
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Stripe Monthly Price ID</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.stripe_price_id_monthly}
                onChange={(e) => setForm({ ...form, stripe_price_id_monthly: e.target.value })}
                placeholder="price_xxx (leave blank if not configured)"
              />
            </label>
            <label className="block space-y-1">
              <div className="text-slate-200">Stripe Yearly Price ID</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.stripe_price_id_yearly}
                onChange={(e) => setForm({ ...form, stripe_price_id_yearly: e.target.value })}
                placeholder="price_xxx (leave blank if not configured)"
              />
            </label>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setEditId(null)} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={save} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
