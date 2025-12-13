"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, authHeaders } from "../../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import JsonViewer from "../../../components/JsonViewer";

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
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: "", price: "", features: "{}", quotas: "{}" });
  const [parseError, setParseError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const auth = useMemo(() => authHeaders(), []);

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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openEdit = (plan: any) => {
    setEditId(plan.id);
    setForm({
      name: plan.name || "",
      price: plan.price_monthly ?? "",
      features: JSON.stringify(plan.features || {}, null, 2),
      quotas: JSON.stringify(plan.quotas || {}, null, 2),
    });
    setParseError(null);
    setSuccess(null);
    setError(null);
  };

  const save = async () => {
    setParseError(null);
    let featuresObj = null;
    let quotasObj = null;
    try {
      featuresObj = form.features ? JSON.parse(form.features) : {};
    } catch (e: any) {
      setParseError("Features JSON invalid");
      return;
    }
    try {
      quotasObj = form.quotas ? JSON.parse(form.quotas) : {};
    } catch (e: any) {
      setParseError("Quotas JSON invalid");
      return;
    }
    const priceVal = form.price === "" ? null : Number(form.price);
    if (form.price !== "" && Number.isNaN(priceVal)) {
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

  return (
    <div className="space-y-4">
      {error && <div className="text-red-400 text-sm">{error}</div>}
      {success && <div className="text-emerald-400 text-sm">{success}</div>}
      {loading && <div className="text-slate-400 text-sm">Loading...</div>}

      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.id || plan.key}>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <div className="text-xs text-slate-400">{plan.key}</div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>Price: {plan.price_monthly ?? "-"}</div>
              <div className="text-slate-400">Features</div>
              <JsonViewer value={plan.features || {}} />
              <div className="text-slate-400">Quotas</div>
              <JsonViewer value={plan.quotas || {}} />
              <Button variant="ghost" onClick={() => openEdit(plan)}>
                Edit
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {editId !== null && (
        <Modal onClose={() => setEditId(null)}>
          <div className="p-4 space-y-3 text-sm">
            <div className="text-lg font-semibold">Edit plan</div>
            {parseError && <div className="text-red-400">{parseError}</div>}
            {error && <div className="text-red-400">{error}</div>}
            <label className="block space-y-1">
              <div>Name</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <label className="block space-y-1">
              <div>Price (monthly)</div>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="leave blank for none"
              />
            </label>
            <label className="block space-y-1">
              <div>Features (JSON)</div>
              <textarea
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 font-mono text-xs min-h-[120px]"
                value={form.features}
                onChange={(e) => setForm({ ...form, features: e.target.value })}
              />
            </label>
            <label className="block space-y-1">
              <div>Quotas (JSON)</div>
              <textarea
                className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 font-mono text-xs min-h-[120px]"
                value={form.quotas}
                onChange={(e) => setForm({ ...form, quotas: e.target.value })}
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