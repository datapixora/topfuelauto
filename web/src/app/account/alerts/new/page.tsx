"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import TopNav from "../../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { createAlert } from "../../../../lib/api";
import { useAuth } from "../../../../components/auth/AuthProvider";

export default function NewAlertPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [form, setForm] = useState({
    name: "",
    q: "",
    make: "",
    model: "",
    year_min: "",
    year_max: "",
    price_min: "",
    price_max: "",
    location: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user && !loading) {
      router.replace("/login?next=/account/alerts/new");
    }
  }, [user, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setSaving(true);
    setError(null);
    try {
      const query: Record<string, any> = {};
      if (form.q) query.q = form.q;
      if (form.make) query.make = form.make;
      if (form.model) query.model = form.model;
      if (form.year_min) query.year_min = Number(form.year_min);
      if (form.year_max) query.year_max = Number(form.year_max);
      if (form.price_min) query.price_min = Number(form.price_min);
      if (form.price_max) query.price_max = Number(form.price_max);
      if (form.location) query.location = form.location;

      const alert = await createAlert({
        name: form.name || undefined,
        query,
        is_active: true,
      });
      router.push(`/account/alerts/${alert.id}`);
    } catch (e: any) {
      const message = e?.message || "Unable to create alert";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <TopNav />
      <Card className="border border-slate-800 bg-slate-900">
        <CardHeader>
          <CardTitle className="text-xl text-slate-50">New alert</CardTitle>
          <p className="text-sm text-slate-400">Save a search and we will notify you when new matches appear.</p>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="space-y-2 mb-3">
              <div className="rounded bg-red-500/10 border border-red-500/40 text-red-100 px-3 py-2 text-sm">{error}</div>
              <div className="text-xs text-slate-400">
                If alerts are disabled on your plan,{" "}
                <Link href="/pricing" className="text-brand-accent underline">
                  view plans to upgrade.
                </Link>
              </div>
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-200">
                <span>Name (optional)</span>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="My GT-R alerts"
                />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Keywords</span>
                <Input value={form.q} onChange={(e) => setForm({ ...form, q: e.target.value })} placeholder="search text" required />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Make</span>
                <Input value={form.make} onChange={(e) => setForm({ ...form, make: e.target.value })} placeholder="Nissan" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Model</span>
                <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="GT-R" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Year min</span>
                <Input value={form.year_min} onChange={(e) => setForm({ ...form, year_min: e.target.value })} placeholder="2005" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Year max</span>
                <Input value={form.year_max} onChange={(e) => setForm({ ...form, year_max: e.target.value })} placeholder="2024" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Price min</span>
                <Input value={form.price_min} onChange={(e) => setForm({ ...form, price_min: e.target.value })} placeholder="10000" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Price max</span>
                <Input value={form.price_max} onChange={(e) => setForm({ ...form, price_max: e.target.value })} placeholder="80000" />
              </label>
              <label className="space-y-1 text-sm text-slate-200">
                <span>Location</span>
                <Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="San Francisco" />
              </label>
            </div>

            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => router.back()} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Create alert"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
