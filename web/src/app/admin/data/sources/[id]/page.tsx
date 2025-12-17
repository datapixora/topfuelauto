"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { getDataSource, listSourceRuns, toggleDataSource, deleteDataSource, runDataSource, updateDataSource, listProxies } from "../../../../../lib/api";
import { DataSource, DataRun, ProxyEndpoint } from "../../../../../lib/types";
import AutoDetectPanel from "./AutoDetectPanel";
import ExtractorTemplatePanel from "./ExtractorTemplatePanel";

export default function SourceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const sourceId = Number(params.id);

  const [source, setSource] = useState<DataSource | null>(null);
  const [runs, setRuns] = useState<DataRun[]>([]);
  const [proxies, setProxies] = useState<ProxyEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingRules, setSavingRules] = useState(false);
  const [mergeRules, setMergeRules] = useState({
    auto_merge_enabled: false,
    require_year_make_model: true,
    require_price_or_url: true,
    min_confidence_score: "" as number | "" | null,
  });

  const [showFullBaseUrl, setShowFullBaseUrl] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied">("idle");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourceData, runsData, proxyData] = await Promise.all([
        getDataSource(sourceId),
        listSourceRuns(sourceId),
        listProxies(),
      ]);
      setSource(sourceData);
      setRuns(runsData);
      setProxies(proxyData || []);

      const rules = sourceData.merge_rules || {};
      setMergeRules({
        auto_merge_enabled: rules.auto_merge_enabled ?? false,
        require_year_make_model: rules.require_year_make_model ?? true,
        require_price_or_url: rules.require_price_or_url ?? true,
        min_confidence_score: rules.min_confidence_score ?? "",
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [sourceId]);

  const handleToggle = async () => {
    try {
      await toggleDataSource(sourceId);
      await loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async () => {
    if (!source) return;
    if (!confirm(`Delete source "${source.name}"? This will also delete all runs and staged items.`)) {
      return;
    }
    try {
      await deleteDataSource(sourceId);
      router.push("/admin/data/sources");
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRun = async () => {
    if (!source) return;
    if (!source.is_enabled) {
      setError("Cannot run a disabled source. Enable it first.");
      return;
    }
    try {
      setError(null);
      await runDataSource(sourceId);
      // Reload to see the new run
      setTimeout(() => loadData(), 1000);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSaveRules = async () => {
    setSavingRules(true);
    try {
      await updateDataSource(sourceId, {
        merge_rules: {
          auto_merge_enabled: mergeRules.auto_merge_enabled,
          require_year_make_model: mergeRules.require_year_make_model,
          require_price_or_url: mergeRules.require_price_or_url,
          min_confidence_score:
            mergeRules.min_confidence_score === "" || mergeRules.min_confidence_score === null
              ? null
              : Number(mergeRules.min_confidence_score),
        },
      });
      await loadData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSavingRules(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "text-blue-400";
      case "succeeded":
        return "text-green-400";
      case "failed":
        return "text-red-400";
      case "paused":
        return "text-yellow-400";
      case "blocked":
        return "text-orange-400";
      case "proxy_failed":
        return "text-orange-300";
      default:
        return "text-slate-400";
    }
  };

  const proxyPool = useMemo(() => {
    const enabled = proxies.filter((p) => p.is_enabled);
    return {
      count: enabled.length,
      weight: enabled.reduce((acc, p) => acc + (p.weight || 0), 0),
      lastExit: enabled.find((p) => p.last_exit_ip)?.last_exit_ip,
    };
  }, [proxies]);

  const baseUrlDisplay = useMemo(() => {
    if (!source?.base_url) return "N/A";
    if (showFullBaseUrl) return source.base_url;
    return source.base_url.length > 100 ? `${source.base_url.slice(0, 100)}…` : source.base_url;
  }, [source?.base_url, showFullBaseUrl]);

  const copyBaseUrl = async () => {
    if (!source?.base_url || !navigator?.clipboard) return;
    await navigator.clipboard.writeText(source.base_url);
    setCopyStatus("copied");
    setTimeout(() => setCopyStatus("idle"), 2000);
  };

  if (loading) {
    return <div className="text-slate-400">Loading source details...</div>;
  }

  if (!source) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          ← Back
        </Button>
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400">
          Error: {error || "Source not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" onClick={() => router.back()} className="mb-2">
            ← Back to Sources
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{source.name}</h1>
            <div
              className={`w-3 h-3 rounded-full ${
                source.is_enabled ? "bg-green-500" : "bg-slate-600"
              }`}
              title={source.is_enabled ? "Enabled" : "Disabled"}
            />
          </div>
          <div className="text-xs text-slate-500 font-mono mt-1">{source.key}</div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="primary"
            onClick={handleRun}
            disabled={!source.is_enabled}
          >
            Run Now
          </Button>
          <Button variant="ghost" onClick={handleToggle}>
            {source.is_enabled ? "Disable" : "Enable"}
          </Button>
          <Button variant="ghost" className="text-red-400 hover:text-red-300" onClick={handleDelete}>
            Delete Source
          </Button>
        </div>
      </div>

      {source.disabled_reason && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          <strong>Disabled:</strong> {source.disabled_reason}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm min-w-0">
            <div className="flex justify-between items-start gap-2 min-w-0">
              <span className="text-slate-400">Base URL:</span>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 min-w-0">
                <span className="font-mono text-xs break-words min-w-0">{baseUrlDisplay}</span>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    className="text-xs px-2 py-1"
                    onClick={copyBaseUrl}
                  >
                    {copyStatus === "copied" ? "Copied" : "Copy"}
                  </Button>
                  <Button
                    variant="ghost"
                    className="text-xs px-2 py-1"
                    onClick={() => setShowFullBaseUrl((prev) => !prev)}
                  >
                    {showFullBaseUrl ? "Hide" : "Show full"}
                  </Button>
                </div>
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Mode:</span>
              <span className="font-medium">{source.mode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Schedule:</span>
              <span className="font-medium">{source.schedule_minutes} minutes</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Max items/run:</span>
              <span className="font-medium">{source.max_items_per_run}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Max pages/run:</span>
              <span className="font-medium">{source.max_pages_per_run}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Rate:</span>
              <span className="font-medium">{source.rate_per_minute}/min</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Concurrency:</span>
              <span className="font-medium">{source.concurrency}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Timeout:</span>
              <span className="font-medium">{source.timeout_seconds}s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Retry count:</span>
              <span className="font-medium">{source.retry_count}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm min-w-0">
            <div className="flex justify-between">
              <span className="text-slate-400">Last run:</span>
              <span className="font-medium text-xs">{formatDate(source.last_run_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Next run:</span>
              <span className="font-medium text-xs">{formatDate(source.next_run_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Failure count:</span>
              <span className={`font-medium ${source.failure_count > 0 ? "text-red-400" : ""}`}>
                {source.failure_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Cooldown until:</span>
              <span className="font-medium text-xs">
                {source.cooldown_until ? formatDate(source.cooldown_until) : "None"}
              </span>
            </div>
            {source.last_block_reason && (
              <div className="flex justify-between text-orange-300">
                <span>Last block:</span>
                <span className="text-xs text-right">
                  {source.last_block_reason}
                  {source.last_blocked_at && ` @ ${formatDate(source.last_blocked_at)}`}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Created:</span>
              <span className="font-medium text-xs">{formatDate(source.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Updated:</span>
              <span className="font-medium text-xs">{formatDate(source.updated_at)}</span>
            </div>
            <div className="pt-2 border-t border-slate-800 mt-2">
              <div className="text-xs text-slate-400 mb-1">Proxy Pool</div>
              <div className="text-sm">
                {proxyPool.count > 0 ? (
                  <>
                    {proxyPool.count} enabled (weight {proxyPool.weight})
                    {proxyPool.lastExit && (
                      <span className="text-slate-500 text-xs"> • last exit {proxyPool.lastExit}</span>
                    )}
                  </>
                ) : (
                  "No proxies configured"
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Merge Rules (Auto-Approval)</CardTitle>
          <Button variant="ghost" onClick={handleSaveRules} disabled={savingRules}>
            {savingRules ? "Saving..." : "Save Rules"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={mergeRules.auto_merge_enabled}
              onChange={(e) => setMergeRules({ ...mergeRules, auto_merge_enabled: e.target.checked })}
              className="w-4 h-4"
            />
            <span>Enable auto-approval</span>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={mergeRules.require_year_make_model}
                onChange={(e) => setMergeRules({ ...mergeRules, require_year_make_model: e.target.checked })}
                className="w-4 h-4"
                disabled={!mergeRules.auto_merge_enabled}
              />
              <span>Require year + make + model</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={mergeRules.require_price_or_url}
                onChange={(e) => setMergeRules({ ...mergeRules, require_price_or_url: e.target.checked })}
                className="w-4 h-4"
                disabled={!mergeRules.auto_merge_enabled}
              />
              <span>Require price or URL</span>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">
                Min confidence (0-1)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={mergeRules.min_confidence_score ?? ""}
                onChange={(e) =>
                  setMergeRules({
                    ...mergeRules,
                    min_confidence_score: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                disabled={!mergeRules.auto_merge_enabled}
              />
              <p className="text-xs text-slate-500 mt-1">Leave blank to ignore confidence.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <AutoDetectPanel sourceId={sourceId} initialSettingsJson={source.settings_json} onSourceUpdated={loadData} />

      <ExtractorTemplatePanel sourceId={sourceId} initialSettingsJson={source.settings_json} onSourceUpdated={loadData} />

      {source.settings_json && Object.keys(source.settings_json).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Settings JSON</CardTitle>
          </CardHeader>
          <CardContent className="min-w-0">
            <div className="max-h-[320px] overflow-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs whitespace-pre-wrap break-words">
              <pre className="m-0">
                {JSON.stringify(source.settings_json, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Run History ({runs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <div className="text-center py-6 text-slate-400 text-sm">No runs yet</div>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded hover:bg-slate-800 cursor-pointer transition"
                  onClick={() => router.push(`/admin/data/runs/${run.id}`)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${getStatusColor(run.status)}`}>
                        {run.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-slate-500">#{run.id}</span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Started: {formatDate(run.started_at)} {run.finished_at && `• Finished: ${formatDate(run.finished_at)}`}
                    </div>
                  </div>
                  <div className="text-sm space-y-1 text-right">
                    <div>
                      <span className="text-slate-400">Pages:</span>{" "}
                      <span className="font-medium">{run.pages_done}/{run.pages_planned}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Items:</span>{" "}
                      <span className="font-medium">{run.items_found} found, {run.items_staged} staged</span>
                    </div>
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
