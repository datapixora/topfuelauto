"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { detectDataSource, updateDataSource } from "../../../../../lib/api";

type DetectCandidate = {
  strategy_key: string;
  confidence?: number;
  reason?: string;
};

type DetectReport = {
  requested_url?: string | null;
  url?: string | null;
  used_url?: string | null;
  fetch?: {
    method?: string;
    title?: string | null;
    status_code?: number | null;
    final_url?: string | null;
    html_len?: number | null;
  };
  snippet?: string | null;
  fingerprints?: Record<string, boolean>;
  signals?: Record<string, any>;
  candidates?: DetectCandidate[];
  detected_strategy?: string | null;
  suggested_settings_patch?: Record<string, any>;
  attempts?: Array<{
    chosen_best?: boolean;
    method?: string;
    use_proxy?: boolean;
    status_code?: number | null;
    final_url?: string | null;
    html_len?: number | null;
    title?: string | null;
    blocked?: boolean;
    block_reason?: string | null;
    error?: string | null;
  }>;
};

export default function AutoDetectPanel(props: {
  sourceId: number;
  initialSettingsJson?: Record<string, any> | null;
  onSourceUpdated?: () => void;
}) {
  const router = useRouter();

  const initialReport = useMemo(
    () => (props.initialSettingsJson?.detect_report as DetectReport | undefined) || null,
    [props.initialSettingsJson]
  );
  const initialDetectedStrategy = useMemo(() => {
    const s = props.initialSettingsJson?.detected_strategy || initialReport?.detected_strategy;
    return typeof s === "string" ? s : "";
  }, [props.initialSettingsJson, initialReport]);

  const initialFetch = useMemo(() => {
    const fetchCfg = props.initialSettingsJson?.fetch;
    return {
      useProxy: typeof fetchCfg?.use_proxy === "boolean" ? fetchCfg.use_proxy : false,
      usePlaywright: typeof fetchCfg?.use_playwright === "boolean" ? fetchCfg.use_playwright : true,
    };
  }, [props.initialSettingsJson]);

  const initialTestUrl = useMemo(() => {
    const targets = props.initialSettingsJson?.targets;
    const val = targets?.test_url;
    return typeof val === "string" ? val : "";
  }, [props.initialSettingsJson]);

  const [testUrl, setTestUrl] = useState(initialTestUrl);
  const [detectTryProxy, setDetectTryProxy] = useState(initialFetch.useProxy);
  const [detectTryPlaywright, setDetectTryPlaywright] = useState(initialFetch.usePlaywright);
  const [detectLoading, setDetectLoading] = useState(false);
  const [detectResult, setDetectResult] = useState<DetectReport | null>(initialReport);
  const [selectedStrategy, setSelectedStrategy] = useState<string>(initialDetectedStrategy);
  const [applyingStrategy, setApplyingStrategy] = useState(false);
  const [applyingSuggested, setApplyingSuggested] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setDetectResult(initialReport);
  }, [initialReport]);

  useEffect(() => {
    setSelectedStrategy(initialDetectedStrategy);
  }, [initialDetectedStrategy]);

  useEffect(() => {
    setTestUrl(initialTestUrl);
  }, [initialTestUrl]);

  useEffect(() => {
    setDetectTryProxy(initialFetch.useProxy);
    setDetectTryPlaywright(initialFetch.usePlaywright);
  }, [initialFetch.useProxy, initialFetch.usePlaywright]);

  const handleDetect = async () => {
    setDetectLoading(true);
    setLocalError(null);
    try {
      const result = (await detectDataSource(props.sourceId, {
        url: testUrl.trim() || undefined,
        try_proxy: detectTryProxy,
        try_playwright: detectTryPlaywright,
      })) as DetectReport;
      setDetectResult(result);
      setSelectedStrategy(result?.detected_strategy || "");
      const usedUrl = typeof result.used_url === "string" ? result.used_url : (result.fetch?.final_url || "");
      if (usedUrl) setTestUrl(usedUrl);
      await props.onSourceUpdated?.();
      router.refresh();
    } catch (e: any) {
      setLocalError(e.message || "Detect failed");
    } finally {
      setDetectLoading(false);
    }
  };

  const handleApplyStrategy = async () => {
    if (!selectedStrategy) return;
    setApplyingStrategy(true);
    setLocalError(null);
    try {
      await updateDataSource(props.sourceId, {
        settings_json: { detected_strategy: selectedStrategy },
      });
      await props.onSourceUpdated?.();
      router.refresh();
    } catch (e: any) {
      setLocalError(e.message || "Apply failed");
    } finally {
      setApplyingStrategy(false);
    }
  };

  const handleApplySuggested = async () => {
    const patch = detectResult?.suggested_settings_patch;
    if (!patch || typeof patch !== "object") return;
    setApplyingSuggested(true);
    setLocalError(null);
    try {
      await updateDataSource(props.sourceId, { settings_json: patch });
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`de_extract_autotest_${props.sourceId}`, "1");
        sessionStorage.setItem(`de_extract_banner_${props.sourceId}`, "1");
      }
      await props.onSourceUpdated?.();
      router.refresh();
    } catch (e: any) {
      setLocalError(e.message || "Apply suggested template failed");
    } finally {
      setApplyingSuggested(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Auto-Detect</CardTitle>
        <Button variant="ghost" onClick={handleDetect} disabled={detectLoading}>
          {detectLoading ? "Detecting..." : "Run Detect"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="text-xs font-mono text-green-400">AUTO-DETECT-PANEL-ON</div>

        {localError && (
          <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
            Error: {localError}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">
              Test URL
            </label>
            <input
              type="text"
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
              placeholder="https://example.com/listings"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">
              Single source of truth for Detect, Test Extract, and Save Template (stored in settings_json.targets.test_url).
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-slate-400">Options</div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={detectTryProxy}
                onChange={(e) => setDetectTryProxy(e.target.checked)}
                className="w-4 h-4"
              />
              <span>Try proxy (if configured)</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={detectTryPlaywright}
                onChange={(e) => setDetectTryPlaywright(e.target.checked)}
                className="w-4 h-4"
              />
              <span>Try Playwright fallback</span>
            </label>
            <div className="text-xs text-slate-500">
              Detected strategy:{" "}
              <span className="font-mono">
                {(props.initialSettingsJson?.detected_strategy as string) || "—"}
              </span>
            </div>
          </div>
        </div>

        {detectResult ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Fetch</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Method:</span>
                    <span className="font-mono">{detectResult.fetch?.method || "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Status:</span>
                    <span className="font-mono">{detectResult.fetch?.status_code ?? "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">HTML len:</span>
                    <span className="font-mono">{detectResult.fetch?.html_len ?? "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Final URL:</span>
                    <span className="font-mono break-all">{detectResult.fetch?.final_url || "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Title:</span>
                    <span className="font-mono break-all">{detectResult.fetch?.title || "—"}</span>
                  </div>
                </div>
              </div>

              <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Fingerprints</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  {Object.entries(detectResult.fingerprints || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-2">
                      <span className="text-slate-400">{key}:</span>
                      <span className={value ? "text-green-400" : "text-slate-500"}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {detectResult.signals && (
              <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Signals</div>
                <pre className="m-0 text-xs whitespace-pre-wrap break-words">
                  {JSON.stringify(detectResult.signals, null, 2)}
                </pre>
              </div>
            )}

            <div className="rounded border border-slate-800 bg-slate-950 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Snippet (first 200 chars)</div>
              <pre className="m-0 text-xs whitespace-pre-wrap break-words">{detectResult.snippet || ""}</pre>
            </div>

            <div className="space-y-2">
              <div className="text-xs uppercase tracking-wide text-slate-400">Candidates</div>
              <div className="space-y-2">
                {(detectResult.candidates || []).map((c: DetectCandidate) => (
                  <label
                    key={c.strategy_key}
                    className="flex items-start gap-3 rounded border border-slate-800 bg-slate-900/30 p-3"
                  >
                    <input
                      type="radio"
                      name="detected_strategy"
                      checked={selectedStrategy === c.strategy_key}
                      onChange={() => setSelectedStrategy(c.strategy_key)}
                      className="mt-1 w-4 h-4"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs break-all">{c.strategy_key}</span>
                        <span className="text-xs text-slate-400">{Math.round((c.confidence || 0) * 100)}%</span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">{c.reason}</div>
                    </div>
                  </label>
                ))}
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="ghost"
                  onClick={() => setSelectedStrategy(detectResult?.detected_strategy || selectedStrategy)}
                  disabled={!detectResult?.detected_strategy}
                >
                  Select Best
                </Button>
                <Button variant="primary" onClick={handleApplyStrategy} disabled={applyingStrategy || !selectedStrategy}>
                  {applyingStrategy ? "Applying..." : "Apply"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleApplySuggested}
                  disabled={applyingSuggested || !detectResult?.suggested_settings_patch}
                >
                  {applyingSuggested ? "Applying..." : "Apply Suggested Template"}
                </Button>
              </div>

              {detectResult?.attempts && (
                <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                  <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Attempts</div>
                  <div className="space-y-2">
                    {detectResult.attempts.map((a, idx) => (
                      <div
                        key={`${a.method || "attempt"}-${idx}`}
                        className={
                          "rounded border p-2 text-xs " +
                          (a.chosen_best ? "border-green-700 bg-green-900/10" : "border-slate-800 bg-slate-950/30")
                        }
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="font-mono">
                            {a.chosen_best ? "BEST " : ""}
                            {a.method || "—"}
                            {a.use_proxy ? " (proxy)" : ""}
                          </div>
                          <div className="text-slate-400 font-mono">
                            status={a.status_code ?? "—"} len={a.html_len ?? "—"}
                          </div>
                        </div>
                        <div className="mt-1 text-slate-500 break-all">{a.final_url || "—"}</div>
                        {a.title && <div className="mt-1 text-slate-400 break-all">title={a.title}</div>}
                        {(a.blocked || a.error) && (
                          <div className="mt-1 text-red-300">
                            {a.blocked ? `blocked (${a.block_reason || "—"})` : ""}
                            {a.blocked && a.error ? " | " : ""}
                            {a.error ? `error: ${a.error}` : ""}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-slate-500 text-xs">No detect report yet. Click “Run Detect” to analyze the source.</div>
        )}
      </CardContent>
    </Card>
  );
}
