"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { createProxy, listProxies, updateProxy, checkProxy, checkAllProxies } from "../../../lib/api";
import { ProxyEndpoint } from "../../../lib/types";

const emptyForm = {
  id: null as number | null,
  name: "",
  host: "",
  port: 3120,
  scheme: "http",
  username: "",
  password: "",
  is_enabled: true,
  weight: 1,
  max_concurrency: 1,
  region: "",
};

export default function ProxiesPage() {
  const [proxies, setProxies] = useState<ProxyEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listProxies();
      setProxies(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const pool = useMemo(() => {
    const enabled = proxies.filter((p) => p.is_enabled);
    return {
      enabledCount: enabled.length,
      weightSum: enabled.reduce((acc, p) => acc + (p.weight || 0), 0),
    };
  }, [proxies]);

  const startCreate = () => {
    setForm(emptyForm);
  };

  const startEdit = (p: ProxyEndpoint) => {
    setForm({
      id: p.id,
      name: p.name,
      host: p.host,
      port: p.port,
      scheme: p.scheme,
      username: p.username || "",
      password: "",
      is_enabled: p.is_enabled,
      weight: p.weight,
      max_concurrency: p.max_concurrency,
      region: p.region || "",
    });
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload: any = {
        name: form.name,
        host: form.host,
        port: Number(form.port),
        scheme: form.scheme,
        username: form.username || null,
        is_enabled: form.is_enabled,
        weight: Number(form.weight),
        max_concurrency: Number(form.max_concurrency),
        region: form.region || null,
      };
      if (form.password) payload.password = form.password;
      if (form.id) {
        await updateProxy(form.id, payload);
      } else {
        payload.password = form.password; // required on create if provided
        await createProxy(payload);
      }
      await load();
      setForm(emptyForm);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const doCheck = async (id: number) => {
    setChecking(true);
    try {
      await checkProxy(id);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  };

  const doCheckAll = async () => {
    setChecking(true);
    try {
      await checkAllProxies();
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  };

  const statusColor = (status?: string | null) => {
    if (status === "ok") return "text-green-400";
    if (status === "failed") return "text-red-400";
    return "text-slate-400";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Proxies</h1>
          <p className="text-sm text-slate-400">Manage outbound proxy pool and health checks</p>
        </div>
        <div className="flex gap-2 items-center text-sm text-slate-300">
          <div className="px-3 py-1 rounded bg-slate-800 border border-slate-700">
            Pool: {pool.enabledCount} enabled / weight {pool.weightSum}
          </div>
          <Button onClick={doCheckAll} disabled={checking} variant="ghost">
            {checking ? "Checking..." : "Check all"}
          </Button>
          <Button onClick={startCreate}>New Proxy</Button>
        </div>
      </div>

      {error && <div className="bg-red-900/30 border border-red-800 p-3 text-red-300 text-sm">{error}</div>}

      <Card>
        <CardHeader>
          <CardTitle>{form.id ? `Edit Proxy #${form.id}` : "Create Proxy"}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="text-sm text-slate-300">Name</label>
            <input className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Host</label>
            <input className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Port</label>
            <input type="number" className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Scheme</label>
            <select className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.scheme} onChange={(e) => setForm({ ...form, scheme: e.target.value })}>
              <option value="http">http</option>
              <option value="https">https</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-300">Username</label>
            <input className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Password (write-only)</label>
            <input type="password" className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <p className="text-xs text-slate-500">Will not be shown again; leave blank to keep existing</p>
          </div>
          <div className="flex items-center gap-2 mt-6">
            <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} />
            <span className="text-sm text-slate-300">Enabled</span>
          </div>
          <div>
            <label className="text-sm text-slate-300">Weight</label>
            <input type="number" min={1} className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.weight} onChange={(e) => setForm({ ...form, weight: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Max Concurrency</label>
            <input type="number" min={1} className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.max_concurrency} onChange={(e) => setForm({ ...form, max_concurrency: Number(e.target.value) })} />
          </div>
          <div>
            <label className="text-sm text-slate-300">Region/Tags</label>
            <input className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
          </div>
          <div className="md:col-span-3 flex gap-2">
            <Button onClick={save} disabled={saving}>{saving ? "Saving..." : form.id ? "Update" : "Create"}</Button>
            <Button variant="ghost" onClick={() => setForm(emptyForm)}>Clear</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Proxy Pool</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <div className="text-slate-400 text-sm">Loading...</div>
          ) : proxies.length === 0 ? (
            <div className="text-slate-500 text-sm">No proxies configured.</div>
          ) : (
            <div className="space-y-2">
              {proxies.map((p) => (
                <div key={p.id} className="p-3 rounded border border-slate-800 bg-slate-900/40 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div>
                    <div className="font-semibold flex items-center gap-2">
                      {p.name}
                      <span className={`text-xs px-2 py-1 rounded ${p.is_enabled ? "bg-green-900/30 text-green-300" : "bg-slate-800 text-slate-400"}`}>
                        {p.is_enabled ? "Enabled" : "Disabled"}
                      </span>
                      <span className={`text-xs ${statusColor(p.last_check_status)}`}>
                        {p.last_check_status || "unknown"}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 font-mono">{p.scheme}://{p.host}:{p.port}</div>
                    <div className="text-xs text-slate-400">Weight {p.weight} • Max conc {p.max_concurrency} {p.region && `• ${p.region}`}</div>
                    {p.last_exit_ip && <div className="text-xs text-slate-300">Exit IP: {p.last_exit_ip}</div>}
                    {p.last_error && <div className="text-xs text-red-300">Error: {p.last_error}</div>}
                    {p.last_check_at && <div className="text-xs text-slate-500">Last check: {new Date(p.last_check_at).toLocaleString()}</div>}
                  </div>
                  <div className="flex gap-2 text-sm">
                    <Button variant="ghost" onClick={() => doCheck(p.id)} disabled={checking}>Check</Button>
                    <Button variant="ghost" onClick={() => updateProxy(p.id, { is_enabled: !p.is_enabled }).then(load)}>
                      {p.is_enabled ? "Disable" : "Enable"}
                    </Button>
                    <Button variant="ghost" onClick={() => startEdit(p)}>Edit</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

