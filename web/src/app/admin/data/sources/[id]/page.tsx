"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { getDataSource, listSourceRuns, toggleDataSource, deleteDataSource, runDataSource } from "../../../../../lib/api";
import { DataSource, DataRun } from "../../../../../lib/types";

export default function SourceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const sourceId = Number(params.id);

  const [source, setSource] = useState<DataSource | null>(null);
  const [runs, setRuns] = useState<DataRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourceData, runsData] = await Promise.all([
        getDataSource(sourceId),
        listSourceRuns(sourceId),
      ]);
      setSource(sourceData);
      setRuns(runsData);
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
      default:
        return "text-slate-400";
    }
  };

  if (loading) {
    return <div className="text-slate-400">Loading source details...</div>;
  }

  if (error || !source) {
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
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Base URL:</span>
              <span className="font-mono text-xs">{source.base_url}</span>
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
          <CardContent className="space-y-2 text-sm">
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
              <span className="text-slate-400">Created:</span>
              <span className="font-medium text-xs">{formatDate(source.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Updated:</span>
              <span className="font-medium text-xs">{formatDate(source.updated_at)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {source.settings_json && Object.keys(source.settings_json).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Settings JSON</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-slate-900 p-3 rounded overflow-x-auto">
              {JSON.stringify(source.settings_json, null, 2)}
            </pre>
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
