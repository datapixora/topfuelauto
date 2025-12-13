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
  const [form, setForm] = useState({ name: "", price: "", features: "{}", quotas: "{}" });
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
