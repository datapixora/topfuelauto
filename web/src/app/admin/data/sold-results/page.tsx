"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { Label } from "../../../../components/ui/label";
import {
  createBidfaxJob,
  listAuctionTracking,
  retryAuctionTracking,
  testBidfaxParse,
} from "../../../../lib/api";
import type { AuctionTracking } from "../../../../lib/types";

export default function SoldResultsPage() {
  const [trackings, setTrackings] = useState<AuctionTracking[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [targetUrl, setTargetUrl] = useState("");
  const [pages, setPages] = useState(1);
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [creating, setCreating] = useState(false);

  // Test parse state
  const [testUrl, setTestUrl] = useState("");
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const loadTrackings = async () => {
    setLoading(true);
    try {
      const data = await listAuctionTracking({ limit: 50 });
      setTrackings(data.trackings || []);
      setCounts(data.counts || {});
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTrackings();
  }, []);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await createBidfaxJob({
        target_url: targetUrl,
        pages,
        make: make || undefined,
        model: model || undefined,
        schedule_enabled: scheduleEnabled,
        schedule_interval_minutes: scheduleEnabled ? intervalMinutes : undefined,
      });

      // Reset form
      setTargetUrl("");
      setPages(1);
      setMake("");
      setModel("");

      // Reload trackings
      await loadTrackings();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleRetry = async (trackingId: number) => {
    try {
      await retryAuctionTracking(trackingId, false);
      await loadTrackings();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleTestParse = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testBidfaxParse(testUrl);
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "done": return "text-green-500";
      case "running": return "text-blue-500";
      case "failed": return "text-red-500";
      case "pending": return "text-orange-500";
      default: return "text-slate-400";
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-100">Sold Results (Bidfax)</h1>
        <p className="text-sm text-slate-400">
          Crawl Bidfax sold auction data and store as truth records
        </p>
      </header>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-4 underline">Dismiss</button>
        </div>
      )}

      {/* Status Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        {["pending", "running", "done", "failed"].map((status) => (
          <Card key={status}>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-slate-100">{counts[status] || 0}</div>
              <div className={`text-sm capitalize ${statusColor(status)}`}>{status}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Crawl Job */}
      <Card>
        <CardHeader>
          <CardTitle>Create Crawl Job</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateJob} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="targetUrl">Target URL *</Label>
                <Input
                  id="targetUrl"
                  type="url"
                  placeholder="https://en.bidfax.info/ford/c-max/"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pages">Pages to Crawl *</Label>
                <Input
                  id="pages"
                  type="number"
                  min="1"
                  max="100"
                  value={pages}
                  onChange={(e) => setPages(Number(e.target.value))}
                  required
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="make">Make (optional)</Label>
                <Input
                  id="make"
                  placeholder="Ford"
                  value={make}
                  onChange={(e) => setMake(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model (optional)</Label>
                <Input
                  id="model"
                  placeholder="C-Max"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scheduleEnabled}
                  onChange={(e) => setScheduleEnabled(e.target.checked)}
                />
                <span className="text-sm text-slate-300">Enable Schedule</span>
              </label>
              {scheduleEnabled && (
                <div className="flex items-center gap-2">
                  <Label htmlFor="interval">Interval (minutes)</Label>
                  <Input
                    id="interval"
                    type="number"
                    min="10"
                    value={intervalMinutes}
                    onChange={(e) => setIntervalMinutes(Number(e.target.value))}
                    className="w-24"
                  />
                </div>
              )}
            </div>

            <Button type="submit" disabled={creating}>
              {creating ? "Creating..." : "Start Crawl"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Test URL Parse */}
      <Card>
        <CardHeader>
          <CardTitle>Test URL Parse</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="https://en.bidfax.info/ford/c-max/"
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
              />
              <Button onClick={handleTestParse} disabled={testing || !testUrl}>
                {testing ? "Testing..." : "Test"}
              </Button>
            </div>
            {testResult && (
              <div className="bg-slate-900 border border-slate-700 rounded p-4 text-sm font-mono">
                <pre className="text-slate-300 whitespace-pre-wrap overflow-auto max-h-96">
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tracking List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Tracking</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-slate-400">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-700">
                  <tr className="text-left">
                    <th className="pb-2 text-slate-400">URL</th>
                    <th className="pb-2 text-slate-400">Status</th>
                    <th className="pb-2 text-slate-400">Attempts</th>
                    <th className="pb-2 text-slate-400">Items Saved</th>
                    <th className="pb-2 text-slate-400">Next Check</th>
                    <th className="pb-2 text-slate-400">Error</th>
                    <th className="pb-2 text-slate-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {trackings.map((t) => (
                    <tr key={t.id} className="border-b border-slate-800">
                      <td className="py-2 text-slate-300 max-w-xs truncate" title={t.target_url}>
                        {t.target_url}
                      </td>
                      <td className={`py-2 capitalize ${statusColor(t.status)}`}>
                        {t.status}
                      </td>
                      <td className="py-2 text-slate-400">{t.attempts}</td>
                      <td className="py-2 text-slate-400">{t.stats?.items_saved || 0}</td>
                      <td className="py-2 text-slate-400 text-xs">
                        {t.next_check_at ? new Date(t.next_check_at).toLocaleString() : "—"}
                      </td>
                      <td className="py-2 text-red-400 text-xs max-w-xs truncate" title={t.last_error || ""}>
                        {t.last_error || "—"}
                      </td>
                      <td className="py-2">
                        {t.status === "failed" && (
                          <Button
                            variant="ghost"
                            onClick={() => handleRetry(t.id)}
                            className="text-xs"
                          >
                            Retry
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
