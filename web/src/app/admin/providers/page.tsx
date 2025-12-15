"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import { listProviderSettings, updateProviderSetting, seedProviderDefaults } from "../../../lib/api";

type Provider = {
  key: string;
  enabled: boolean;
  priority: number;
  mode: string;
};

const MODES = [
  { value: "both", label: "Both" },
  { value: "search", label: "Search only" },
  { value: "assist", label: "Assist only" },
];

export default function AdminProviders() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listProviderSettings();
      setProviders(rows || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const updateRow = (idx: number, patch: Partial<Provider>) => {
    setProviders((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  };

  const save = async (row: Provider, idx: number) => {
    setSavingKey(row.key);
    setError(null);
    try {
      const updated = await updateProviderSetting(row.key, {
        enabled: row.enabled,
        priority: row.priority,
        mode: row.mode,
      });
      updateRow(idx, updated as Provider);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSavingKey(null);
    }
  };

  const seed = async () => {
    setSeeding(true);
    setError(null);
    try {
      await seedProviderDefaults();
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Provider Manager</CardTitle>
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={load} disabled={loading}>
            Reload
          </Button>
          <Button onClick={seed} disabled={seeding}>
            {seeding ? "Seeding..." : "Seed defaults"}
          </Button>
          {error && <div className="text-red-400 text-xs">Error: {error}</div>}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading && <div className="text-slate-400 text-sm">Loading providers…</div>}
        <Table>
          <THead>
            <TR>
              <TH>Key</TH>
              <TH>Enabled</TH>
              <TH>Mode</TH>
              <TH>Priority</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {providers.map((p, idx) => (
              <TR key={p.key}>
                <TD className="font-mono text-xs">{p.key}</TD>
                <TD>
                  <input
                    type="checkbox"
                    checked={p.enabled}
                    onChange={(e) => updateRow(idx, { enabled: e.target.checked })}
                  />
                </TD>
                <TD>
                  <select
                    className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={p.mode}
                    onChange={(e) => updateRow(idx, { mode: e.target.value })}
                  >
                    {MODES.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </TD>
                <TD>
                  <input
                    type="number"
                    className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={p.priority}
                    onChange={(e) => updateRow(idx, { priority: Number(e.target.value) })}
                  />
                </TD>
                <TD>
                  <Button onClick={() => save(p, idx)} disabled={savingKey === p.key}>
                    {savingKey === p.key ? "Saving..." : "Save"}
                  </Button>
                </TD>
              </TR>
            ))}
            {!loading && providers.length === 0 && (
              <TR>
                <TD colSpan={5} className="text-slate-500 text-sm py-6 text-center">
                  No providers configured yet.
                </TD>
              </TR>
            )}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
