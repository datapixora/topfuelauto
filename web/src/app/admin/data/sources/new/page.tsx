"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { createDataSource, getProxyOptions } from "../../../../../lib/api";

type ProxyOption = {
  id: number;
  name: string;
  host: string;
  port: number;
  scheme: string;
  last_check_status: string | null;
  last_exit_ip: string | null;
};

export default function NewSourcePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [proxyOptions, setProxyOptions] = useState<ProxyOption[]>([]);
  const [loadingProxies, setLoadingProxies] = useState(true);

  const [formData, setFormData] = useState({
    key: "",
    name: "",
    base_url: "",
    mode: "list_only" as "list_only" | "follow_details",
    schedule_minutes: 60,
    max_items_per_run: 100,
    max_pages_per_run: 10,
    rate_per_minute: 30,
    concurrency: 2,
    timeout_seconds: 30,
    retry_count: 3,
    is_enabled: true,
    auto_merge_enabled: false,
    require_year_make_model: true,
    require_price_or_url: true,
    min_confidence_score: "" as number | "" | null,
    // Proxy settings - use Proxy Pool
    proxy_mode: "NONE" as "NONE" | "POOL",
    proxy_id: null as number | null,
  });

  // Fetch proxy options on mount
  useEffect(() => {
    async function fetchProxies() {
      try {
        const proxies = await getProxyOptions();
        setProxyOptions(proxies);
      } catch (e) {
        console.error("Failed to fetch proxy options:", e);
      } finally {
        setLoadingProxies(false);
      }
    }
    fetchProxies();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const merge_rules = {
        auto_merge_enabled: formData.auto_merge_enabled,
        require_year_make_model: formData.require_year_make_model,
        require_price_or_url: formData.require_price_or_url,
        min_confidence_score:
          formData.min_confidence_score === "" || formData.min_confidence_score === null
            ? null
            : Number(formData.min_confidence_score),
      };

      const payload = {
        key: formData.key,
        name: formData.name,
        base_url: formData.base_url,
        mode: formData.mode,
        schedule_minutes: formData.schedule_minutes,
        max_items_per_run: formData.max_items_per_run,
        max_pages_per_run: formData.max_pages_per_run,
        rate_per_minute: formData.rate_per_minute,
        concurrency: formData.concurrency,
        timeout_seconds: formData.timeout_seconds,
        retry_count: formData.retry_count,
        is_enabled: formData.is_enabled,
        proxy_mode: formData.proxy_mode,
        proxy_id: formData.proxy_mode === "POOL" ? formData.proxy_id : null,
        merge_rules,
      };

      await createDataSource(payload);
      router.push("/admin/data/sources");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="space-y-4">
      <div>
        <Button variant="ghost" onClick={() => router.back()} className="mb-2">
          ← Back to Sources
        </Button>
        <h1 className="text-2xl font-semibold">Create Data Source</h1>
        <p className="text-sm text-slate-400">Configure a new scraping source with optional proxy</p>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Basic Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Key <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  placeholder="copart_us"
                  value={formData.key}
                  onChange={(e) => setFormData({ ...formData, key: e.target.value })}
                />
                <p className="text-xs text-slate-500 mt-1">Unique identifier (lowercase, no spaces)</p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  placeholder="Copart US"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Base URL <span className="text-red-400">*</span>
              </label>
              <input
                type="url"
                required
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm font-mono"
                placeholder="https://www.example.com/listings"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              />
              <p className="text-xs text-slate-500 mt-1">
                The scraper will append <code className="text-slate-400">?page=1</code>, <code className="text-slate-400">?page=2</code>, etc. for pagination.
                Include existing query params if needed (e.g., <code className="text-slate-400">https://site.com/cars?sort=date</code> becomes <code className="text-slate-400">?sort=date&page=1</code>)
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1">Mode</label>
                <select
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.mode}
                  onChange={(e) => setFormData({ ...formData, mode: e.target.value as "list_only" | "follow_details" })}
                >
                  <option value="list_only">List Only</option>
                  <option value="follow_details">Follow Details</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Schedule (minutes)</label>
                <input
                  type="number"
                  min="15"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.schedule_minutes}
                  onChange={(e) => setFormData({ ...formData, schedule_minutes: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_enabled"
                checked={formData.is_enabled}
                onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="is_enabled" className="text-sm">Enable source immediately</label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Merge Rules (Auto-Approval)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto_merge_enabled"
                checked={formData.auto_merge_enabled}
                onChange={(e) => setFormData({ ...formData, auto_merge_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="auto_merge_enabled" className="text-sm">
                Enable auto-approval (keeps items in staging but marks them ready to merge)
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="require_year_make_model"
                  checked={formData.require_year_make_model}
                  onChange={(e) => setFormData({ ...formData, require_year_make_model: e.target.checked })}
                  className="w-4 h-4"
                  disabled={!formData.auto_merge_enabled}
                />
                <label htmlFor="require_year_make_model" className="text-sm">
                  Require year + make + model
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="require_price_or_url"
                  checked={formData.require_price_or_url}
                  onChange={(e) => setFormData({ ...formData, require_price_or_url: e.target.checked })}
                  className="w-4 h-4"
                  disabled={!formData.auto_merge_enabled}
                />
                <label htmlFor="require_price_or_url" className="text-sm">
                  Require price or URL
                </label>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Min confidence (0-1, optional)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.min_confidence_score ?? ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      min_confidence_score: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                  disabled={!formData.auto_merge_enabled}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Leave blank to ignore confidence score.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rate Limits & Concurrency</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Max Items/Run</label>
                <input
                  type="number"
                  min="1"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.max_items_per_run}
                  onChange={(e) => setFormData({ ...formData, max_items_per_run: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Max Pages/Run</label>
                <input
                  type="number"
                  min="1"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.max_pages_per_run}
                  onChange={(e) => setFormData({ ...formData, max_pages_per_run: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Rate/Minute</label>
                <input
                  type="number"
                  min="1"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.rate_per_minute}
                  onChange={(e) => setFormData({ ...formData, rate_per_minute: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Concurrency</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.concurrency}
                  onChange={(e) => setFormData({ ...formData, concurrency: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Timeout (seconds)</label>
                <input
                  type="number"
                  min="5"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.timeout_seconds}
                  onChange={(e) => setFormData({ ...formData, timeout_seconds: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Retry Count</label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                  value={formData.retry_count}
                  onChange={(e) => setFormData({ ...formData, retry_count: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Proxy Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Proxy Mode</label>
              <select
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                value={formData.proxy_mode}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    proxy_mode: e.target.value as "NONE" | "POOL",
                    proxy_id: e.target.value === "NONE" ? null : formData.proxy_id,
                  })
                }
              >
                <option value="NONE">No Proxy</option>
                <option value="POOL">Use Proxy from Pool</option>
              </select>
            </div>

            {formData.proxy_mode === "POOL" && (
              <div>
                <label className="block text-sm font-medium mb-1">Select Proxy</label>
                {loadingProxies ? (
                  <div className="text-sm text-slate-400">Loading proxies...</div>
                ) : proxyOptions.length === 0 ? (
                  <div className="bg-yellow-900/20 border border-yellow-800 rounded p-3 text-yellow-400 text-sm">
                    No proxies configured.{" "}
                    <a href="/admin/proxies" className="underline">
                      Go to Admin → Proxies
                    </a>{" "}
                    to add proxies first.
                  </div>
                ) : (
                  <>
                    <select
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      value={formData.proxy_id ?? ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          proxy_id: e.target.value ? parseInt(e.target.value) : null,
                        })
                      }
                    >
                      <option value="">-- Select a proxy --</option>
                      {proxyOptions.map((proxy) => (
                        <option key={proxy.id} value={proxy.id}>
                          {proxy.name} ({proxy.scheme}://{proxy.host}:{proxy.port})
                          {proxy.last_check_status === "success" && " ✓"}
                          {proxy.last_check_status === "failed" && " ✗"}
                        </option>
                      ))}
                    </select>
                    {formData.proxy_id && (
                      <p className="text-xs text-slate-400 mt-1">
                        Proxy credentials are managed in the Proxy Pool. Sources do not store credentials.
                      </p>
                    )}
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex gap-2">
          <Button type="submit" disabled={loading}>
            {loading ? "Creating..." : "Create Source"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
