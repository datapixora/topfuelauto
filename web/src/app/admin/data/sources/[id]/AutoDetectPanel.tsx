"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "../../../../../components/ui/table";
import { detectDataSource, testExtractDataSource, updateDataSource } from "../../../../../lib/api";

type DetectCandidate = {
  strategy_key: string;
  confidence?: number;
  reason?: string;
};

type DetectReport = {
  requested_url?: string | null;
  url?: string | null;
  used_url?: string | null;
  errors?: string[];
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

type ExtractConfig = {
  strategy: string;
  list: {
    item_selector: string;
    next_page_selector?: string;
  };
  fields: {
    title?: { selector?: string | null; attr?: string };
    price?: { selector?: string | null; attr?: string };
    url?: { selector?: string | null; attr?: string };
    image?: { selector?: string | null; attr?: string };
  };
  normalize?: Record<string, any>;
};

type TestExtractResponse = {
  requested_url?: string | null;
  url?: string | null;
  used_url?: string | null;
  fetch?: {
    method?: string;
    status_code?: number | null;
    final_url?: string | null;
    html_len?: number | null;
  };
  items_found?: number;
  items_preview?: Array<Record<string, any>>;
  errors?: string[];
};

const normalizeExtract = (raw: any): ExtractConfig => {
  const strategy = typeof raw?.strategy === "string" ? raw.strategy : "generic_html_list";
  const list = (raw?.list && typeof raw.list === "object") ? raw.list : {};
  const fields = (raw?.fields && typeof raw.fields === "object") ? raw.fields : {};
  const normalize = (raw?.normalize && typeof raw.normalize === "object") ? raw.normalize : {};

  const item_selector = typeof list.item_selector === "string" ? list.item_selector : "";
  const next_page_selector = typeof list.next_page_selector === "string" ? list.next_page_selector : "";

  return {
    strategy,
    list: {
      item_selector,
      ...(next_page_selector ? { next_page_selector } : {}),
    },
    fields: fields as any,
    normalize,
  };
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

  const [suggestedStrategy, setSuggestedStrategy] = useState<string>("");
  const [suggestedItemSelector, setSuggestedItemSelector] = useState<string>("");
  const [suggestedNextPageSelector, setSuggestedNextPageSelector] = useState<string>("");
  const [suggestedTitleSelector, setSuggestedTitleSelector] = useState<string>("");
  const [suggestedPriceSelector, setSuggestedPriceSelector] = useState<string>("");
  const [suggestedUrlSelector, setSuggestedUrlSelector] = useState<string>("");
  const [suggestedImageSelector, setSuggestedImageSelector] = useState<string>("");

  const [templateTesting, setTemplateTesting] = useState(false);
  const [templateResult, setTemplateResult] = useState<TestExtractResponse | null>(null);

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

  useEffect(() => {
    const patch = detectResult?.suggested_settings_patch;
    const extractRaw = patch && typeof patch === "object" ? (patch as any).extract : null;
    if (!extractRaw || typeof extractRaw !== "object") {
      setSuggestedStrategy("");
      setSuggestedItemSelector("");
      setSuggestedNextPageSelector("");
      setSuggestedTitleSelector("");
      setSuggestedPriceSelector("");
      setSuggestedUrlSelector("");
      setSuggestedImageSelector("");
      setTemplateResult(null);
      return;
    }

    const normalized = normalizeExtract(extractRaw);
    setSuggestedStrategy(normalized.strategy || "");
    setSuggestedItemSelector(normalized.list.item_selector || "");
    setSuggestedNextPageSelector(normalized.list.next_page_selector || "");

    const fields: any = normalized.fields || {};
    setSuggestedTitleSelector(typeof fields?.title?.selector === "string" ? fields.title.selector : "");
    setSuggestedPriceSelector(typeof fields?.price?.selector === "string" ? fields.price.selector : "");
    setSuggestedUrlSelector(typeof fields?.url?.selector === "string" ? fields.url.selector : "");
    setSuggestedImageSelector(typeof fields?.image?.selector === "string" ? fields.image.selector : "");

    setTemplateResult(null);
  }, [detectResult?.suggested_settings_patch]);

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

  const buildSuggestedExtract = (): ExtractConfig => ({
    strategy: suggestedStrategy || (detectResult?.detected_strategy || "generic_html_list"),
    list: {
      item_selector: suggestedItemSelector,
      ...(suggestedNextPageSelector ? { next_page_selector: suggestedNextPageSelector } : {}),
    },
    fields: {
      title: { selector: suggestedTitleSelector.trim() || null, attr: "text" },
      price: { selector: suggestedPriceSelector.trim() || null, attr: "text" },
      url: { selector: suggestedUrlSelector.trim() || null, attr: "href" },
      image: { selector: suggestedImageSelector.trim() || null, attr: "src" },
    },
    normalize: {},
  });

  const buildSuggestedPatch = (): Record<string, any> => {
    const base = detectResult?.suggested_settings_patch;
    const patch = base && typeof base === "object" ? { ...(base as any) } : {};
    const existingTargets = patch.targets && typeof patch.targets === "object" ? patch.targets : {};

    patch.targets = { ...existingTargets, test_url: testUrl.trim() };
    patch.extract = buildSuggestedExtract();
    patch.detected_strategy = detectResult?.detected_strategy || patch.detected_strategy;
    return patch;
  };

  const handleTestSuggested = async () => {
    const urlForTest = testUrl.trim();
    if (!urlForTest) {
      setLocalError("Missing Test URL. Set it above first.");
      return;
    }

    const extractForTest = buildSuggestedExtract();
    if (!extractForTest?.list?.item_selector?.trim()) {
      setLocalError("Missing item selector in suggested template.");
      return;
    }

    setTemplateTesting(true);
    setLocalError(null);
    try {
      const res = (await testExtractDataSource(props.sourceId, {
        url: urlForTest,
        extract: extractForTest,
      })) as TestExtractResponse;
      setTemplateResult(res);
    } catch (e: any) {
      setLocalError(e.message || "Test extract failed");
    } finally {
      setTemplateTesting(false);
    }
  };

  const handleApplySuggested = async () => {
    const base = detectResult?.suggested_settings_patch;
    if (!base || typeof base !== "object") return;

    const urlForTest = testUrl.trim();
    if (!urlForTest) {
      setLocalError("Missing Test URL. Set it above first.");
      return;
    }

    const extractForApply = buildSuggestedExtract();
    if (!extractForApply?.list?.item_selector?.trim()) {
      setLocalError("Missing item selector in suggested template.");
      return;
    }

    setApplyingSuggested(true);
    setLocalError(null);
    try {
      const patch = buildSuggestedPatch();
      await updateDataSource(props.sourceId, { settings_json: patch });
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`de_extract_autotest_${props.sourceId}`, "1");
        sessionStorage.setItem(`de_extract_banner_${props.sourceId}`, "1");
      }
      await props.onSourceUpdated?.();
      router.refresh();

      // Auto-run Test Extract after apply to show immediate feedback.
      setTemplateTesting(true);
      try {
        const res = (await testExtractDataSource(props.sourceId, {
          url: urlForTest,
          extract: extractForApply,
        })) as TestExtractResponse;
        setTemplateResult(res);
      } catch (e: any) {
        setLocalError(e.message || "Auto Test Extract failed");
      } finally {
        setTemplateTesting(false);
      }
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
                {(props.initialSettingsJson?.detected_strategy as string) || "-"}
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
                    <span className="font-mono">{detectResult.fetch?.method || "-"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Status:</span>
                    <span className="font-mono">{detectResult.fetch?.status_code ?? "-"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">HTML len:</span>
                    <span className="font-mono">{detectResult.fetch?.html_len ?? "-"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Final URL:</span>
                    <span className="font-mono break-all">{detectResult.fetch?.final_url || "-"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Title:</span>
                    <span className="font-mono break-all">{detectResult.fetch?.title || "-"}</span>
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

            {(detectResult.errors || []).length > 0 && (
              <div className="rounded border border-slate-800 bg-slate-950 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Warnings</div>
                <ul className="list-disc pl-5 space-y-1 text-xs text-slate-400">
                  {(detectResult.errors || []).map((msg, idx) => (
                    <li key={idx} className="break-words">{msg}</li>
                  ))}
                </ul>
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
              </div>

              {detectResult?.suggested_settings_patch && (
                <div className="rounded border border-slate-800 bg-slate-900/30 p-3 space-y-4 mt-3">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-400">Suggested Template (Editable)</div>
                      <div className="text-xs text-slate-500 mt-1">
                        Strategy: <span className="font-mono">{suggestedStrategy || "-"}</span> | Test URL:{" "}
                        <span className="font-mono break-all">{testUrl.trim() || "-"}</span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        Edit selectors here, then apply to persist into <span className="font-mono">settings_json.extract</span>.
                      </div>
                    </div>
                    <div className="flex gap-2 items-center justify-end">
                      <Button variant="ghost" onClick={handleTestSuggested} disabled={templateTesting}>
                        {templateTesting ? "Testing..." : "Test Extract"}
                      </Button>
                      <Button
                        variant="primary"
                        onClick={handleApplySuggested}
                        disabled={applyingSuggested || !testUrl.trim() || !suggestedItemSelector.trim()}
                      >
                        {applyingSuggested ? "Applying..." : "Apply Suggested Template"}
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Item selector</label>
                      <input
                        type="text"
                        value={suggestedItemSelector}
                        onChange={(e) => {
                          setSuggestedItemSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder="li.product"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">
                        Next page selector (optional)
                      </label>
                      <input
                        type="text"
                        value={suggestedNextPageSelector}
                        onChange={(e) => {
                          setSuggestedNextPageSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder="a.next"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Title selector</label>
                      <input
                        type="text"
                        value={suggestedTitleSelector}
                        onChange={(e) => {
                          setSuggestedTitleSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder="h2"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Price selector</label>
                      <input
                        type="text"
                        value={suggestedPriceSelector}
                        onChange={(e) => {
                          setSuggestedPriceSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder=".price"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">URL selector</label>
                      <input
                        type="text"
                        value={suggestedUrlSelector}
                        onChange={(e) => {
                          setSuggestedUrlSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder="a[href]"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Uses href.</p>
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Image selector</label>
                      <input
                        type="text"
                        value={suggestedImageSelector}
                        onChange={(e) => {
                          setSuggestedImageSelector(e.target.value);
                          setTemplateResult(null);
                        }}
                        placeholder="img"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Uses src.</p>
                    </div>
                  </div>

                  {templateResult && (
                    <div className="space-y-3">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="rounded border border-slate-800 bg-slate-950 p-3">
                          <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Test Extract</div>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between gap-2">
                              <span className="text-slate-400">Items found:</span>
                              <span className="font-mono">{templateResult.items_found ?? 0}</span>
                            </div>
                            <div className="flex justify-between gap-2">
                              <span className="text-slate-400">Final URL:</span>
                              <span className="font-mono break-all">
                                {templateResult.fetch?.final_url || templateResult.used_url || "-"}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="rounded border border-slate-800 bg-slate-950 p-3">
                          <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Fetch</div>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between gap-2">
                              <span className="text-slate-400">Method:</span>
                              <span className="font-mono">{templateResult.fetch?.method || "-"}</span>
                            </div>
                            <div className="flex justify-between gap-2">
                              <span className="text-slate-400">Status:</span>
                              <span className="font-mono">{templateResult.fetch?.status_code ?? "-"}</span>
                            </div>
                            <div className="flex justify-between gap-2">
                              <span className="text-slate-400">HTML len:</span>
                              <span className="font-mono">{templateResult.fetch?.html_len ?? "-"}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {(templateResult.errors || []).length > 0 && (
                        <div className="rounded border border-slate-800 bg-slate-950 p-3">
                          <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Errors</div>
                          <ul className="list-disc pl-5 space-y-1 text-xs text-slate-400">
                            {(templateResult.errors || []).map((msg, idx) => (
                              <li key={idx} className="break-words">{msg}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="rounded border border-slate-800 bg-slate-950 overflow-auto">
                        <Table>
                          <THead>
                            <TR>
                              <TH>Title</TH>
                              <TH>Price</TH>
                              <TH>URL</TH>
                              <TH>Image</TH>
                            </TR>
                          </THead>
                          <TBody>
                            {(templateResult.items_preview || []).length === 0 ? (
                              <TR>
                                <TD colSpan={4} className="text-slate-500">
                                  No preview items.
                                </TD>
                              </TR>
                            ) : (
                              (templateResult.items_preview || []).slice(0, 5).map((row, idx) => (
                                <TR key={idx}>
                                  <TD className="text-xs">{row.title || "-"}</TD>
                                  <TD className="text-xs">{row.price || "-"}</TD>
                                  <TD className="text-xs break-all">{row.url || "-"}</TD>
                                  <TD className="text-xs break-all">{row.image || "-"}</TD>
                                </TR>
                              ))
                            )}
                          </TBody>
                        </Table>
                      </div>
                    </div>
                  )}
                </div>
              )}

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
                            {a.method || "-"}
                            {a.use_proxy ? " (proxy)" : ""}
                          </div>
                          <div className="text-slate-400 font-mono">
                            status={a.status_code ?? "-"} len={a.html_len ?? "-"}
                          </div>
                        </div>
                        <div className="mt-1 text-slate-500 break-all">{a.final_url || "-"}</div>
                        {a.title && <div className="mt-1 text-slate-400 break-all">title={a.title}</div>}
                        {(a.blocked || a.error) && (
                          <div className="mt-1 text-red-300">
                            {a.blocked ? `blocked (${a.block_reason || "-"})` : ""}
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
          <div className="text-slate-500 text-xs">No detect report yet. Click Run Detect to analyze the source.</div>
        )}
      </CardContent>
    </Card>
  );
}
