"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { createDataSource, testProxyConnection } from "../../../../../lib/api";

export default function NewSourcePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testingProxy, setTestingProxy] = useState(false);
  const [proxyTestResult, setProxyTestResult] = useState<{ success: boolean; message: string } | null>(null);

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
    // Proxy settings
    proxy_enabled: false,
    proxy_host: "",
    proxy_port: "",
    proxy_username: "",
    proxy_password: "",
    proxy_type: "http" as "http" | "socks5",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Build settings_json with proxy config and auto-merge
      const settings_json: any = {};

      // Auto-merge setting
      if (formData.auto_merge_enabled) {
        settings_json.auto_merge_enabled = true;
      }

      // Proxy config
      if (formData.proxy_enabled && formData.proxy_host && formData.proxy_port) {
        settings_json.proxy_enabled = true;
        settings_json.proxy_url = `${formData.proxy_type}://${formData.proxy_host}:${formData.proxy_port}`;
        settings_json.proxy_type = formData.proxy_type;
        if (formData.proxy_username) {
          settings_json.proxy_username = formData.proxy_username;
        }
        if (formData.proxy_password) {
          settings_json.proxy_password = formData.proxy_password;
        }
      }

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
        settings_json: Object.keys(settings_json).length > 0 ? settings_json : null,
      };

      await createDataSource(payload);
      router.push("/admin/data/sources");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestProxy = async () => {
    if (!formData.proxy_host || !formData.proxy_port) {
      setProxyTestResult({ success: false, message: "Proxy host and port are required" });
      return;
    }

    setTestingProxy(true);
    setProxyTestResult(null);

    try {
      const proxyUrl = `${formData.proxy_type}://${formData.proxy_host}:${formData.proxy_port}`;
      const data = await testProxyConnection({
        proxy_url: proxyUrl,
        proxy_username: formData.proxy_username || null,
        proxy_password: formData.proxy_password || null,
      });

      setProxyTestResult({
        success: data.success,
        message: data.message + (data.latency_ms ? ` (${data.latency_ms}ms)` : ""),
      });
    } catch (e: any) {
      setProxyTestResult({ success: false, message: e.message });
    } finally {
      setTestingProxy(false);
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

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto_merge_enabled"
                checked={formData.auto_merge_enabled}
                onChange={(e) => setFormData({ ...formData, auto_merge_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="auto_merge_enabled" className="text-sm">
                Enable auto-merge (skip manual review for valid listings)
              </label>
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
            <CardTitle>Proxy Settings (Optional)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="proxy_enabled"
                checked={formData.proxy_enabled}
                onChange={(e) => setFormData({ ...formData, proxy_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="proxy_enabled" className="text-sm font-medium">Enable Proxy</label>
            </div>

            {formData.proxy_enabled && (
              <>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Type</label>
                    <select
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      value={formData.proxy_type}
                      onChange={(e) => setFormData({ ...formData, proxy_type: e.target.value as "http" | "socks5" })}
                    >
                      <option value="http">HTTP</option>
                      <option value="socks5">SOCKS5</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Proxy Server</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm font-mono"
                      placeholder="proxy.smartproxy.net"
                      value={formData.proxy_host}
                      onChange={(e) => setFormData({ ...formData, proxy_host: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Port</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm font-mono"
                      placeholder="3120"
                      value={formData.proxy_port}
                      onChange={(e) => setFormData({ ...formData, proxy_port: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium mb-1">Username (optional)</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      placeholder="proxy_user"
                      value={formData.proxy_username}
                      onChange={(e) => setFormData({ ...formData, proxy_username: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Password (optional)</label>
                    <input
                      type="password"
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      placeholder="••••••••"
                      value={formData.proxy_password}
                      onChange={(e) => setFormData({ ...formData, proxy_password: e.target.value })}
                    />
                    <p className="text-xs text-slate-500 mt-1">Encrypted before storage</p>
                  </div>
                </div>

                <div>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleTestProxy}
                    disabled={testingProxy || !formData.proxy_host || !formData.proxy_port}
                  >
                    {testingProxy ? "Testing..." : "Test Proxy Connection"}
                  </Button>

                  {proxyTestResult && (
                    <div
                      className={`mt-2 p-2 rounded text-sm ${
                        proxyTestResult.success
                          ? "bg-green-900/20 border border-green-800 text-green-400"
                          : "bg-red-900/20 border border-red-800 text-red-400"
                      }`}
                    >
                      {proxyTestResult.message}
                    </div>
                  )}
                </div>
              </>
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
