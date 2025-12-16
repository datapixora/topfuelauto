"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { getDataRun, listRunItems } from "../../../../../lib/api";
import { DataRun, StagedListing } from "../../../../../lib/types";

export default function RunDetailPage() {
  const router = useRouter();
  const params = useParams();
  const runId = Number(params.runId);

  const [run, setRun] = useState<DataRun | null>(null);
  const [items, setItems] = useState<StagedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [runData, itemsData] = await Promise.all([
        getDataRun(runId),
        listRunItems(runId),
      ]);
      setRun(runData);
      setItems(itemsData);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [runId]);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-500";
      case "succeeded":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
      case "paused":
        return "bg-yellow-500";
      case "blocked":
        return "bg-orange-500";
      case "proxy_failed":
        return "bg-orange-300";
      default:
        return "bg-slate-600";
    }
  };

  const getProgressPercent = () => {
    if (!run || run.pages_planned === 0) return 0;
    return Math.round((run.pages_done / run.pages_planned) * 100);
  };

  if (loading) {
    return <div className="text-slate-400">Loading run details...</div>;
  }

  if (error || !run) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          ← Back
        </Button>
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400">
          Error: {error || "Run not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" onClick={() => router.back()} className="mb-2">
            ← Back
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">Run #{run.id}</h1>
            <div
              className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}
            >
              {run.status.toUpperCase()}
            </div>
          </div>
          <div className="text-sm text-slate-400 mt-1">
            Source ID: {run.source_id}
          </div>
        </div>
      </div>

      {run.error_summary && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          <strong>Error:</strong> {run.error_summary}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400">Pages</span>
                <span className="font-medium">{run.pages_done}/{run.pages_planned}</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${getProgressPercent()}%` }}
                />
              </div>
              <div className="text-xs text-slate-500 text-right mt-1">{getProgressPercent()}%</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Items</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Found:</span>
              <span className="font-medium text-lg">{run.items_found}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Staged:</span>
              <span className="font-medium text-lg text-green-400">{run.items_staged}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Timing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Started:</span>
              <span className="font-medium text-xs">{formatDate(run.started_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Finished:</span>
              <span className="font-medium text-xs">{formatDate(run.finished_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Created:</span>
              <span className="font-medium text-xs">{formatDate(run.created_at)}</span>
            </div>
            <div className="pt-2 border-t border-slate-800 mt-2 text-xs">
              <div className="text-slate-400">Proxy</div>
              <div className="font-mono text-slate-200">
                {run.proxy_id ? `#${run.proxy_id}` : "None"} {run.proxy_exit_ip && ` • exit ${run.proxy_exit_ip}`}
              </div>
              {run.proxy_error && <div className="text-red-300">Error: {run.proxy_error}</div>}
            </div>
          </CardContent>
        </Card>
      </div>

      {run.debug_json && Object.keys(run.debug_json).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Debug Info</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-slate-900 p-3 rounded overflow-x-auto">
              {JSON.stringify(run.debug_json, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Staged Items ({items.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-center py-6 text-slate-400 text-sm">No staged items yet</div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="p-3 bg-slate-800/50 rounded hover:bg-slate-800 transition"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="font-medium">{item.title || "Untitled"}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">
                        {item.source_listing_id && `#${item.source_listing_id} • `}
                        {item.source_key}
                      </div>
                    </div>
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        item.status === "active"
                          ? "bg-green-900/30 text-green-400"
                          : item.status === "ended"
                          ? "bg-slate-700 text-slate-400"
                          : "bg-yellow-900/30 text-yellow-400"
                      }`}
                    >
                      {item.status}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    {item.year && (
                      <div>
                        <span className="text-slate-400">Year:</span>{" "}
                        <span className="font-medium">{item.year}</span>
                      </div>
                    )}
                    {item.make && (
                      <div>
                        <span className="text-slate-400">Make:</span>{" "}
                        <span className="font-medium">{item.make}</span>
                      </div>
                    )}
                    {item.model && (
                      <div>
                        <span className="text-slate-400">Model:</span>{" "}
                        <span className="font-medium">{item.model}</span>
                      </div>
                    )}
                    {item.price_amount && (
                      <div>
                        <span className="text-slate-400">Price:</span>{" "}
                        <span className="font-medium">
                          {item.currency} {item.price_amount.toLocaleString()}
                        </span>
                      </div>
                    )}
                    {item.odometer_value && (
                      <div>
                        <span className="text-slate-400">Odometer:</span>{" "}
                        <span className="font-medium">{item.odometer_value.toLocaleString()}</span>
                      </div>
                    )}
                    {item.location && (
                      <div>
                        <span className="text-slate-400">Location:</span>{" "}
                        <span className="font-medium">{item.location}</span>
                      </div>
                    )}
                  </div>

                  {item.attributes && item.attributes.length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300">
                        Attributes ({item.attributes.length})
                      </summary>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2 text-xs pl-4">
                        {item.attributes.map((attr) => (
                          <div key={attr.id}>
                            <span className="text-slate-500">{attr.key}:</span>{" "}
                            <span className="font-medium">
                              {attr.value_text || attr.value_num || (attr.value_bool !== null ? String(attr.value_bool) : "N/A")}
                              {attr.unit && ` ${attr.unit}`}
                            </span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  <div className="mt-2 text-xs text-slate-500">
                    <a
                      href={item.canonical_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-slate-300 underline"
                    >
                      View source →
                    </a>
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
