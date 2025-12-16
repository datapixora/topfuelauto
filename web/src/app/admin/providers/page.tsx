"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import {
  listProviderSettings,
  updateProviderSetting,
  seedProviderDefaults,
  getWebCrawlProviderConfig,
  updateWebCrawlProviderConfig,
} from "../../../lib/api";
import { WebCrawlProviderConfig } from "../../../lib/types";

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
  const [crawlConfig, setCrawlConfig] = useState<WebCrawlProviderConfig | null>(null);
  const [crawlSaving, setCrawlSaving] = useState(false);
  const [crawlAllowlistText, setCrawlAllowlistText] = useState("");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, crawl] = await Promise.all([listProviderSettings(), getWebCrawlProviderConfig().catch(() => null)]);
      setProviders(rows || []);
      if (crawl) {
        setCrawlConfig(crawl);
        setCrawlAllowlistText((crawl.allowlist || []).join("\n"));
      }
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

  const parseAllowlist = (text: string) =>
    text
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);

  const saveCrawl = async () => {
    if (!crawlConfig) return;
    setCrawlSaving(true);
    setError(null);
    try {
      const updated = await updateWebCrawlProviderConfig({
        ...crawlConfig,
        allowlist: parseAllowlist(crawlAllowlistText),
      });
      setCrawlConfig(updated);
      setCrawlAllowlistText((updated.allowlist || []).join("\n"));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCrawlSaving(false);
    }
  };

  return (
    <div className="space-y-6">
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

      <Card>
        <CardHeader>
          <CardTitle>Web Crawl On-Demand</CardTitle>
          <div className="text-xs text-slate-400">
            Manage allowlist and rate limits for the on-demand crawl provider. URLs must include <code>{`{query}`}</code>
            placeholder.
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {!crawlConfig && <div className="text-slate-400 text-sm">Loading config…</div>}
          {crawlConfig && (
            <>
              <div className="flex items-center gap-3">
                <label className="text-sm">Enabled</label>
                <input
                  type="checkbox"
                  checked={crawlConfig.enabled}
                  onChange={(e) => setCrawlConfig({ ...crawlConfig, enabled: e.target.checked })}
                />
                <label className="text-sm ml-4">Priority</label>
                <input
                  type="number"
                  className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                  value={crawlConfig.priority}
                  onChange={(e) => setCrawlConfig({ ...crawlConfig, priority: Number(e.target.value) })}
                />
              </div>

              <div className="space-y-1">
                <label className="text-sm font-semibold">Allowlist URLs (one per line, must contain {"{query}"})</label>
                <textarea
                  className="w-full min-h-[120px] bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm"
                  value={crawlAllowlistText}
                  onChange={(e) => setCrawlAllowlistText(e.target.value)}
                  placeholder="https://example.com/search?q={query}"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Rate per minute</label>
                  <input
                    type="number"
                    className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={crawlConfig.rate_per_minute}
                    onChange={(e) => setCrawlConfig({ ...crawlConfig, rate_per_minute: Number(e.target.value) })}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Concurrency</label>
                  <input
                    type="number"
                    className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={crawlConfig.concurrency}
                    onChange={(e) => setCrawlConfig({ ...crawlConfig, concurrency: Number(e.target.value) })}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Max sources</label>
                  <input
                    type="number"
                    className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={crawlConfig.max_sources}
                    onChange={(e) => setCrawlConfig({ ...crawlConfig, max_sources: Number(e.target.value) })}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Min results before crawl</label>
                  <input
                    type="number"
                    className="w-28 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={crawlConfig.min_results}
                    onChange={(e) => setCrawlConfig({ ...crawlConfig, min_results: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button onClick={saveCrawl} disabled={crawlSaving}>
                  {crawlSaving ? "Saving..." : "Save crawl config"}
                </Button>
                <Button variant="ghost" onClick={load} disabled={loading}>
                  Reload
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
