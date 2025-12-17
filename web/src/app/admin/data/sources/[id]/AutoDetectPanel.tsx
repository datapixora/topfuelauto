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
  fetch?: {
    method?: string;
    status_code?: number | null;
    final_url?: string | null;
    html_len?: number | null;
  };
  snippet?: string | null;
  fingerprints?: Record<string, boolean>;
  candidates?: DetectCandidate[];
  detected_strategy?: string | null;
  attempts?: Array<{ method?: string }>;
};

export default function AutoDetectPanel(props: {
  sourceId: number;
  initialSettingsJson?: Record<string, any> | null;
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

  const [detectUrl, setDetectUrl] = useState("");
  const [detectTryProxy, setDetectTryProxy] = useState(false);
  const [detectTryPlaywright, setDetectTryPlaywright] = useState(true);
  const [detectLoading, setDetectLoading] = useState(false);
  const [detectResult, setDetectResult] = useState<DetectReport | null>(initialReport);
  const [selectedStrategy, setSelectedStrategy] = useState<string>(initialDetectedStrategy);
  const [applyingStrategy, setApplyingStrategy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setDetectResult(initialReport);
  }, [initialReport]);

  useEffect(() => {
    setSelectedStrategy(initialDetectedStrategy);
  }, [initialDetectedStrategy]);

  const handleDetect = async () => {
    setDetectLoading(true);
    setLocalError(null);
    try {
      const result = (await detectDataSource(props.sourceId, {
        url: detectUrl || undefined,
        try_proxy: detectTryProxy,
        try_playwright: detectTryPlaywright,
      })) as DetectReport;
      setDetectResult(result);
      setSelectedStrategy(result?.detected_strategy || "");
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
      router.refresh();
    } catch (e: any) {
      setLocalError(e.message || "Apply failed");
    } finally {
      setApplyingStrategy(false);
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
              Override URL (optional)
            </label>
            <input
              type="text"
              value={detectUrl}
              onChange={(e) => setDetectUrl(e.target.value)}
              placeholder="https://example.com/listings"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">Leave blank to use the source base URL.</p>
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
              </div>

              {detectResult?.attempts && (
                <div className="text-xs text-slate-500">
                  Attempts: {(detectResult.attempts as any[]).map((a) => a.method).join(", ")}
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

