"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { listDataSources, toggleDataSource, deleteDataSource } from "../../../../lib/api";
import { DataSource } from "../../../../lib/types";

export default function DataSourcesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDataSources();
      setSources(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSources();
  }, []);

  const handleToggle = async (sourceId: number) => {
    try {
      await toggleDataSource(sourceId);
      await loadSources();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (sourceId: number, sourceName: string) => {
    if (!confirm(`Delete source "${sourceName}"? This will also delete all runs and staged items.`)) {
      return;
    }
    try {
      await deleteDataSource(sourceId);
      await loadSources();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Data Sources</h1>
          <p className="text-sm text-slate-400">Manage scraping and import sources</p>
        </div>
        <Button onClick={() => router.push("/admin/data/sources/new")}>
          + Add Source
        </Button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {loading && <div className="text-slate-400 text-sm">Loading sources...</div>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <Card key={source.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">{source.name}</CardTitle>
                  <div className="text-xs text-slate-500 font-mono mt-1">{source.key}</div>
                </div>
                <div
                  className={`w-3 h-3 rounded-full ${
                    source.is_enabled ? "bg-green-500" : "bg-slate-600"
                  }`}
                  title={source.is_enabled ? "Enabled" : "Disabled"}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Mode:</span>
                  <span className="font-medium">{source.mode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Schedule:</span>
                  <span className="font-medium">{source.schedule_minutes}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Last run:</span>
                  <span className="font-medium text-xs">{formatDate(source.last_run_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Next run:</span>
                  <span className="font-medium text-xs">{formatDate(source.next_run_at)}</span>
                </div>
                {source.cooldown_until && new Date(source.cooldown_until) > new Date() && (
                  <div className="flex justify-between text-orange-300">
                    <span>Cooldown until:</span>
                    <span className="font-medium text-xs">{formatDate(source.cooldown_until)}</span>
                  </div>
                )}
                {source.last_block_reason && (
                  <div className="text-xs text-orange-300 mt-1">
                    Blocked: {source.last_block_reason}
                    {source.last_blocked_at && ` @ ${formatDate(source.last_blocked_at)}`}
                  </div>
                )}
                {source.failure_count > 0 && (
                  <div className="flex justify-between text-red-400">
                    <span>Failures:</span>
                    <span className="font-medium">{source.failure_count}</span>
                  </div>
                )}
                {source.disabled_reason && (
                  <div className="text-xs text-red-400 mt-2 p-2 bg-red-900/20 rounded">
                    {source.disabled_reason}
                  </div>
                )}
              </div>

              <div className="flex gap-2 pt-2 border-t border-slate-800">
                <Button
                  variant="ghost"
                  className="flex-1 text-xs"
                  onClick={() => router.push(`/admin/data/sources/${source.id}`)}
                >
                  View
                </Button>
                <Button
                  variant="ghost"
                  className="flex-1 text-xs"
                  onClick={() => handleToggle(source.id)}
                >
                  {source.is_enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  variant="ghost"
                  className="text-red-400 hover:text-red-300 text-xs"
                  onClick={() => handleDelete(source.id, source.name)}
                >
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {!loading && sources.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          <div className="text-lg mb-2">No data sources configured</div>
          <div className="text-sm">Click &quot;Add Source&quot; to create your first source</div>
        </div>
      )}
    </div>
  );
}
