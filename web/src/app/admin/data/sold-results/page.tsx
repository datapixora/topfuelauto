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
  getProxyOptions,
} from "../../../../lib/api";
import type { AuctionTracking } from "../../../../lib/types";

type ProxyOption = {
  id: number;
  name: string;
  host: string;
  port: number;
  scheme: string;
  last_check_status?: string | null;
  last_exit_ip?: string | null;
};

export default function SoldResultsPage() {
  const [trackings, setTrackings] = useState<AuctionTracking[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Proxy
  const [proxyOptions, setProxyOptions] = useState<ProxyOption[]>([]);
  const [selectedProxyId, setSelectedProxyId] = useState<number | "">("");
  const [proxyWarningDismissed, setProxyWarningDismissed] = useState(false);

  // Test parse state
  const [testUrl, setTestUrl] = useState("");
  const [testFetchMode, setTestFetchMode] = useState<"http" | "browser">("browser");
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [lastTestSuccessUrl, setLastTestSuccessUrl] = useState<string | null>(null);

  // Crawl form state
  const [targetUrl, setTargetUrl] = useState("");
  const [pages, setPages] = useState(1);
  const [crawlFetchMode, setCrawlFetchMode] = useState<"http" | "browser">("http");
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [batchSize, setBatchSize] = useState(2);
  const [rpm, setRpm] = useState(30);
  const [concurrency, setConcurrency] = useState(1);
  const [strategyId, setStrategyId] = useState("default");
  const [creating, setCreating] = useState(false);

  // Retry button state
  const [retryingId, setRetryingId] = useState<number | null>(null);

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

  const loadProxyOptions = async () => {
    try {
      const options = await getProxyOptions();
      setProxyOptions(options || []);
    } catch (e: any) {
      console.error("Failed to load proxy options", e);
    }
  };

  useEffect(() => {
    void loadTrackings();
    void loadProxyOptions();
  }, []);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await createBidfaxJob({
        target_url: targetUrl || lastTestSuccessUrl || "",
        pages,
        fetch_mode: crawlFetchMode,
        schedule_enabled: scheduleEnabled,
        schedule_interval_minutes: scheduleEnabled ? intervalMinutes : undefined,
        proxy_id: selectedProxyId === "" ? null : Number(selectedProxyId),
        batch_size: batchSize,
        rpm,
        concurrency,
        strategy_id: strategyId,
      });

      setTargetUrl("");
      setPages(1);
      setScheduleEnabled(false);
      setLastTestSuccessUrl(null);
      await loadTrackings();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleRetry = async (trackingId: number) => {
    setRetryingId(trackingId);
    try {
      await retryAuctionTracking(trackingId, false);
      await loadTrackings();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRetryingId(null);
    }
  };

  const handleTestParse = async (proxyIdOverride?: number | "") => {
    if (testing) return;
    setTesting(true);
    setTestResult(null);
    const proxyChoice = proxyIdOverride === undefined ? selectedProxyId : proxyIdOverride;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);
    try {
      const result = await testBidfaxParse({
        url: testUrl,
        proxy_id: proxyChoice === "" || proxyChoice === undefined ? null : Number(proxyChoice),
        fetch_mode: testFetchMode,
      }, { signal: controller.signal });
      setTestResult(result);
      if (result?.success || result?.ok) {
        setLastTestSuccessUrl(testUrl);
        setTargetUrl(testUrl);
      }
    } catch (e: any) {
      const message = e?.name === "AbortError" ? "Request timed out (25s)" : e?.message || "Request failed";
      setTestResult({ success: false, error: message });
      console.error("Test parse error", e);
    } finally {
      clearTimeout(timeout);
      setTesting(false);
    }
  };

  const handleTryNextProxy = () => {
    if (!proxyOptions.length) return;
    const currentId = typeof selectedProxyId === "number" ? selectedProxyId : null;
    const currentIndex = proxyOptions.findIndex((p) => p.id === currentId);
    const next = proxyOptions[(currentIndex + 1) % proxyOptions.length] || proxyOptions[0];
    setSelectedProxyId(next?.id ?? "");
    void handleTestParse(next?.id ?? "");
  };

  const handleTryWithoutProxy = () => {
    setSelectedProxyId("");
    void handleTestParse("");
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

  const proxyLabel = (id?: number | null) => {
    if (!id) return "None";
    const found = proxyOptions.find((p) => p.id === id);
    return found ? `${found.name} (#${found.id})` : `Proxy #${id}`;
  };

  const anyRunning = (counts["running"] || 0) > 0;

  const testStatus = (() => {
    if (!testResult) return null;
    if (testResult.success || testResult.ok) return "ok";
    if (testResult.partial) return "partial";
    return "fail";
  })();

  const proxyStage = testResult?.proxy?.stage || testResult?.error?.stage || null;
  const proxyErrorCode = testResult?.proxy?.error_code || testResult?.error?.code || null;
  const proxyLatency = testResult?.proxy?.latency_ms ?? null;
  const httpStatus = testResult?.http?.status || testResult?.status || testResult?.status_code || null;
  const httpLatency = testResult?.http?.latency_ms ?? null;
  const primaryMessage =
    testResult?.error?.message ||
    testResult?.http?.error ||
    testResult?.proxy?.error ||
    testResult?.message ||
    null;

  const copyDebug = () => {
    if (!testResult) return;
    navigator.clipboard?.writeText(JSON.stringify(testResult, null, 2)).catch(() => {});
  };

  const proxyWarningVisible = !proxyWarningDismissed && !selectedProxyId;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Sold Results (Bidfax)</h1>
          <p className="text-sm text-slate-400">Wizard to test and launch Bidfax crawls.</p>
        </div>
        {anyRunning && (
          <div className="flex items-center gap-2 text-green-300 text-sm">
            <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse"></span> Running...
          </div>
        )}
      </header>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-4 underline">Dismiss</button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Proxy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <select
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            value={selectedProxyId}
            onChange={(e) => setSelectedProxyId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">None (not recommended in prod)</option>
            {proxyOptions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.scheme}://{p.host}:{p.port})
              </option>
            ))}
          </select>
          {proxyWarningVisible && (
            <div className="bg-yellow-900/30 border border-yellow-700 text-yellow-200 text-sm p-3 rounded flex justify-between">
              <span>Bidfax blocks Render IPs. Select a proxy to avoid 403s.</span>
              <button className="text-xs underline" onClick={() => setProxyWarningDismissed(true)}>Dismiss</button>
            </div>
          )}
        </CardContent>
      </Card>

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

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Test URL Parse</CardTitle>
          <div className="text-xs text-slate-400">Runs through proxy above.</div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-2">
            <Input
              className="flex-1"
              placeholder="https://en.bidfax.info/ford/c-max/"
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
            />
            <select
              className="px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm min-w-[120px]"
              value={testFetchMode}
              onChange={(e) => setTestFetchMode(e.target.value as "http" | "browser")}
            >
              <option value="http">HTTP</option>
              <option value="browser">Browser</option>
            </select>
            <Button onClick={handleTestParse} disabled={testing || !testUrl}>
              {testing ? "Testing..." : "Test"}
            </Button>
          </div>

          {testResult && (
            <div className="border border-slate-800 rounded p-3 bg-slate-900/60 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`h-3 w-3 rounded-full ${
                      testStatus === "ok" ? "bg-green-400" : testStatus === "partial" ? "bg-amber-400" : "bg-red-400"
                    }`}
                  ></span>
                  <span className="text-sm text-slate-200">
                    {testStatus === "ok" ? "Success" : testStatus === "partial" ? "Partial" : "Failed"}
                  </span>
                </div>
                <div className="flex gap-2">
                  {testStatus === "fail" && proxyOptions.length > 1 && (
                    <Button variant="outline" className="h-8 px-2 text-xs" disabled={testing} onClick={handleTryNextProxy}>
                      Try next proxy
                    </Button>
                  )}
                  {testStatus === "fail" && (
                    <Button variant="ghost" className="h-8 px-2 text-xs" disabled={testing} onClick={handleTryWithoutProxy}>
                      Try without proxy
                    </Button>
                  )}
                  <Button variant="ghost" className="h-8 px-2 text-sm" onClick={copyDebug}>Copy debug</Button>
                  {testResult.success || testResult.ok ? (
                    <Button className="h-8 px-2 text-sm" onClick={() => { setTargetUrl(testUrl); setLastTestSuccessUrl(testUrl); }}>
                      Use this URL for Crawl
                    </Button>
                  ) : null}
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-2 text-sm text-slate-200">
                <div>
                  HTTP: {httpStatus ?? "n/a"} {httpLatency ? `(${httpLatency} ms)` : ""}
                </div>
                <div>Fetch Mode: <span className="capitalize">{testResult.debug?.fetch_mode || testResult.fetch_mode || testFetchMode}</span></div>
                <div>Proxy: {testResult.proxy?.proxy_name || proxyLabel(testResult.proxy?.proxy_id || (selectedProxyId === "" ? undefined : Number(selectedProxyId)))} </div>
                <div>Proxy stage: {proxyStage || "n/a"}</div>
                <div>Error code: {proxyErrorCode || "-"}</div>
                <div>Proxy latency: {proxyLatency ? `${proxyLatency} ms` : "-"}</div>
                <div>Exit IP: {testResult.proxy?.exit_ip || testResult.proxy_exit_ip || testResult.exit_ip || "-"}</div>
                <div className="md:col-span-3">Message: {primaryMessage || "-"}</div>
              </div>




              {Array.isArray(testResult.preview) && testResult.preview.length > 0 && (
                <div className="bg-slate-800/60 border border-slate-700 rounded p-3">
                  <div className="text-xs uppercase text-slate-400 mb-2">Preview</div>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm text-slate-100">
                    {testResult.preview.slice(0, 3).map((item: any, idx: number) => (
                      <div key={idx} className="border border-slate-700 rounded p-2">
                        <div className="font-semibold text-slate-200">{item.title || item.vin || "Item"}</div>
                        <div className="text-xs text-slate-400">Status: {item.sale_status || "?"}</div>
                        <div className="text-xs text-slate-400">Bid: {item.final_bid || item.sold_price || "?"}</div>
                        <div className="text-xs text-slate-400">VIN: {item.vin || "?"}</div>
                        <div className="text-xs text-slate-400">Lot: {item.lot_id || "?"}</div>
                        <div className="text-xs text-slate-400">Sold: {item.sold_at || "?"}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Create Crawl Job</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateJob} className="space-y-4">
            <div className="space-y-2">
              <Label>Target URL</Label>
              <Input
                placeholder="Use Test Parse to fill this"
                value={targetUrl || lastTestSuccessUrl || ""}
                onChange={(e) => setTargetUrl(e.target.value)}
                disabled={!testResult?.success && !testResult?.ok && !targetUrl}
              />
              {lastTestSuccessUrl && (
                <p className="text-xs text-green-300">Filled from last successful test.</p>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label>Pages</Label>
                <Input type="number" min={1} max={100} value={pages} onChange={(e) => setPages(Number(e.target.value))} />
              </div>
              <div>
                <Label>Batch size/run</Label>
                <Input type="number" min={1} value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))} />
              </div>
              <div>
                <Label>RPM limit</Label>
                <Input type="number" min={1} value={rpm} onChange={(e) => setRpm(Number(e.target.value))} />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <Label>Concurrency</Label>
                <Input type="number" min={1} value={concurrency} onChange={(e) => setConcurrency(Number(e.target.value))} />
              </div>
              <div className="flex items-center gap-2 mt-6">
                <input type="checkbox" checked={scheduleEnabled} onChange={(e) => setScheduleEnabled(e.target.checked)} />
                <span className="text-sm text-slate-300">Enable schedule</span>
              </div>
              {scheduleEnabled && (
                <div>
                  <Label>Run every (minutes)</Label>
                  <Input type="number" min={1} value={intervalMinutes} onChange={(e) => setIntervalMinutes(Number(e.target.value))} />
                </div>
              )}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Fetch Mode</Label>
                <select
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={crawlFetchMode}
                  onChange={(e) => setCrawlFetchMode(e.target.value as "http" | "browser")}
                >
                  <option value="http">HTTP (faster, may be blocked)</option>
                  <option value="browser">Browser (slower, bypasses blocks)</option>
                </select>
                <p className="text-xs text-slate-500">Use Browser mode if HTTP gets 403 errors.</p>
              </div>

              <div className="space-y-2">
                <Label>Strategy</Label>
                <select
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={strategyId}
                  onChange={(e) => setStrategyId(e.target.value)}
                >
                  <option value="default">Default Bidfax Strategy</option>
                </select>
                <p className="text-xs text-slate-500">TODO: load strategies from API when available.</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Proxy (uses global selection)</Label>
              <Input disabled value={selectedProxyId ? proxyLabel(Number(selectedProxyId)) : "None"} />
            </div>

            <Button type="submit" disabled={creating || (!targetUrl && !lastTestSuccessUrl)}>
              {creating ? "Creating..." : "Start Crawl"}
            </Button>
          </form>
        </CardContent>
      </Card>

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
                    <th className="pb-2 text-slate-400">Proxy</th>
                    <th className="pb-2 text-slate-400">Exit IP</th>
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
                      <td className="py-2 text-slate-400">{proxyLabel(t.proxy_id)}</td>
                      <td className="py-2 text-slate-400 text-xs">{t.proxy_exit_ip || "-"}</td>
                      <td className="py-2 text-slate-400">{t.attempts}</td>
                      <td className="py-2 text-slate-400">{t.stats?.items_saved || 0}</td>
                      <td className="py-2 text-slate-400 text-xs">
                        {t.next_check_at ? new Date(t.next_check_at).toLocaleString() : "-"}
                      </td>
                      <td className="py-2 text-red-400 text-xs max-w-xs truncate" title={t.last_error || t.proxy_error || ""}>
                        {t.last_error || t.proxy_error || "-"}
                      </td>
                      <td className="py-2">
                        {t.status === "failed" && (
                          <Button
                            variant="ghost"
                            className={`text-xs ${retryingId === t.id ? "text-green-300" : "text-slate-200"}`}
                            onClick={() => handleRetry(t.id)}
                            disabled={retryingId === t.id}
                          >
                            {retryingId === t.id ? "Retrying..." : "Retry"}
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

