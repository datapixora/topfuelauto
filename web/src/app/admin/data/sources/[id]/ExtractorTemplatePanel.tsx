"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "../../../../../components/ui/table";
import { runDataSource, saveTemplateDataSource, testExtractDataSource } from "../../../../../lib/api";

type ExtractConfig = {
  strategy: string;
  list: {
    item_selector: string;
    next_page_selector?: string;
  };
  fields: {
    title?: { selector: string; attr?: string };
    price?: { selector: string; attr?: string };
    url?: { selector: string; attr?: string };
    image?: { selector: string; attr?: string };
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

type SaveTemplateResponse = TestExtractResponse & {
  saved?: boolean;
  settings_json_patch_applied?: Record<string, any>;
};

const normalizeExtract = (raw: any): ExtractConfig => {
  const strategy = typeof raw?.strategy === "string" ? raw.strategy : "generic_html_list";
  const list = (raw?.list && typeof raw.list === "object") ? raw.list : {};
  const fields = (raw?.fields && typeof raw.fields === "object") ? raw.fields : {};
  const normalize = (raw?.normalize && typeof raw.normalize === "object") ? raw.normalize : {};

  const item_selector = typeof list.item_selector === "string" ? list.item_selector : (typeof raw?.item_selector === "string" ? raw.item_selector : "");
  const next_page_selector =
    typeof list.next_page_selector === "string"
      ? list.next_page_selector
      : (typeof raw?.next_page_selector === "string" ? raw.next_page_selector : "");

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

export default function ExtractorTemplatePanel(props: {
  sourceId: number;
  initialSettingsJson?: Record<string, any> | null;
  onSourceUpdated?: () => void;
}) {
  const router = useRouter();

  const detectedStrategy = useMemo(() => {
    const s = props.initialSettingsJson?.detected_strategy;
    return typeof s === "string" ? s : "";
  }, [props.initialSettingsJson]);

  const sharedTestUrl = useMemo(() => {
    const targets = props.initialSettingsJson?.targets;
    const val = targets?.test_url;
    return typeof val === "string" ? val : "";
  }, [props.initialSettingsJson]);

  const initialExtract = useMemo(
    () => normalizeExtract(props.initialSettingsJson?.extract || {}),
    [props.initialSettingsJson]
  );

  const [itemSelector, setItemSelector] = useState(initialExtract.list.item_selector || "");
  const [nextPageSelector, setNextPageSelector] = useState(initialExtract.list.next_page_selector || "");
  const [extractStrategy, setExtractStrategy] = useState(initialExtract.strategy || "generic_html_list");
  const [titleSelector, setTitleSelector] = useState(
    (initialExtract.fields?.title?.selector as string) || ""
  );
  const [priceSelector, setPriceSelector] = useState(
    (initialExtract.fields?.price?.selector as string) || ""
  );
  const [urlSelector, setUrlSelector] = useState(
    (initialExtract.fields?.url?.selector as string) || ""
  );
  const [imageSelector, setImageSelector] = useState(
    (initialExtract.fields?.image?.selector as string) || ""
  );

  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<TestExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedOk, setSavedOk] = useState(false);
  const [runQueued, setRunQueued] = useState<string | null>(null);
  const [showAppliedBanner, setShowAppliedBanner] = useState(false);

  useEffect(() => {
    const next = normalizeExtract(props.initialSettingsJson?.extract || {});
    setItemSelector(next.list.item_selector || "");
    setNextPageSelector(next.list.next_page_selector || "");
    setExtractStrategy(next.strategy || "generic_html_list");
    setTitleSelector((next.fields?.title?.selector as string) || "");
    setPriceSelector((next.fields?.price?.selector as string) || "");
    setUrlSelector((next.fields?.url?.selector as string) || "");
    setImageSelector((next.fields?.image?.selector as string) || "");
    setSavedOk(false);
    setRunQueued(null);

    if (typeof window !== "undefined") {
      const bannerKey = `de_extract_banner_${props.sourceId}`;
      if (sessionStorage.getItem(bannerKey) === "1") {
        sessionStorage.removeItem(bannerKey);
        setShowAppliedBanner(true);
      } else {
        setShowAppliedBanner(false);
      }

      const autoKey = `de_extract_autotest_${props.sourceId}`;
      if (sessionStorage.getItem(autoKey) === "1") {
        sessionStorage.removeItem(autoKey);

        const urlForTest = sharedTestUrl.trim() || undefined;
        const extractForTest = next;
        if (!urlForTest) {
          setError("Missing Test URL. Set it in Auto-Detect and apply the suggested template again.");
          return;
        }
        if (!extractForTest?.list?.item_selector) {
          setError("Missing item selector. Apply Suggested Template or set extract.list.item_selector manually.");
          return;
        }

        void (async () => {
          setTesting(true);
          setError(null);
          try {
            const res = (await testExtractDataSource(props.sourceId, {
              url: urlForTest,
              extract: extractForTest,
            })) as TestExtractResponse;
            setResult(res);
          } catch (e: any) {
            setError(e.message || "Test extract failed");
          } finally {
            setTesting(false);
          }
        })();
      }
    }
  }, [props.initialSettingsJson, props.sourceId]);

  const buildConfig = (): ExtractConfig => ({
    strategy: extractStrategy || "generic_html_list",
    list: {
      item_selector: itemSelector,
      ...(nextPageSelector ? { next_page_selector: nextPageSelector } : {}),
    },
    fields: {
      title: { selector: titleSelector, attr: "text" },
      price: { selector: priceSelector, attr: "text" },
      url: { selector: urlSelector, attr: "href" },
      image: { selector: imageSelector, attr: "src" },
    },
    normalize: {},
  });

  const preview = result?.items_preview || [];

  const saveUrl = useMemo(() => {
    const fromSettings = sharedTestUrl.trim();
    if (fromSettings) return fromSettings;
    const fromUsed = result?.used_url;
    if (typeof fromUsed === "string" && fromUsed.trim()) return fromUsed.trim();
    const fromFetch = result?.fetch?.final_url;
    return typeof fromFetch === "string" ? fromFetch : "";
  }, [sharedTestUrl, result?.used_url, result?.fetch?.final_url]);

  const canSave = !!saveUrl && (preview.length > 0 || !!sharedTestUrl.trim());

  const handleTest = async () => {
    setTesting(true);
    setError(null);
    setSavedOk(false);
    setRunQueued(null);
    try {
      const res = (await testExtractDataSource(props.sourceId, {
        url: sharedTestUrl.trim() || undefined,
        extract: buildConfig(),
      })) as TestExtractResponse;
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Test extract failed");
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!saveUrl) {
      setError("Missing Test URL. Set it in Auto-Detect or run Test Extract once to capture a final URL.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = (await saveTemplateDataSource(props.sourceId, {
        url: saveUrl,
        extract: buildConfig(),
      })) as SaveTemplateResponse;

      // Ensure UI has a preview even if user saved without running Test Extract first.
      setResult({
        fetch: res.fetch || { final_url: saveUrl },
        items_found: res.items_found,
        items_preview: res.items_preview,
        errors: res.errors,
      });
      setSavedOk(true);
      setRunQueued(null);
      await props.onSourceUpdated?.();
      router.refresh();
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await runDataSource(props.sourceId);
      const taskId = typeof res?.task_id === "string" ? res.task_id : null;
      setRunQueued(taskId ? `Run queued (task_id=${taskId})` : "Run queued");
      await props.onSourceUpdated?.();
      router.refresh();
    } catch (e: any) {
      setError(e.message || "Run failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Extractor Template</CardTitle>
        <div className="flex gap-2 items-center">
          <Button variant="ghost" onClick={handleTest} disabled={testing}>
            {testing ? "Testing..." : "Test Extract"}
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || !canSave}>
            {saving ? "Saving..." : "Save Template"}
          </Button>
          {savedOk && (
            <span className="text-xs text-green-400">Saved ✓</span>
          )}
          {savedOk && (
            <Button variant="ghost" onClick={handleRunNow} disabled={running}>
              {running ? "Running..." : "Run Now"}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {detectedStrategy && (
          <div className="text-xs text-slate-500">
            Detected strategy: <span className="font-mono">{detectedStrategy}</span>. Extract strategy:{" "}
            <span className="font-mono">{extractStrategy || "generic_html_list"}</span>.
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
            Error: {error}
          </div>
        )}

        {runQueued && (
          <div className="rounded border border-slate-800 bg-slate-900/30 p-3 text-xs text-slate-300">
            {runQueued}
          </div>
        )}

        {showAppliedBanner && (
          <div className="rounded border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
            Suggested template applied. Click <span className="font-mono">Test Extract</span> to preview items.
          </div>
        )}

        <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-wide text-slate-400">Test URL</div>
            <div className="font-mono text-xs text-slate-300 break-all">{sharedTestUrl || "—"}</div>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Set this once in the Auto-Detect panel. It is used for Detect, Test Extract, and Save Template.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Item selector</label>
            <input
              type="text"
              value={itemSelector}
              onChange={(e) => {
                setItemSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
              }}
              placeholder=".listing-card"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Next page selector (optional)</label>
            <input
              type="text"
              value={nextPageSelector}
              onChange={(e) => {
                setNextPageSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
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
              value={titleSelector}
              onChange={(e) => {
                setTitleSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
              }}
              placeholder=".title"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Price selector</label>
            <input
              type="text"
              value={priceSelector}
              onChange={(e) => {
                setPriceSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
              }}
              placeholder=".price"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">URL selector</label>
            <input
              type="text"
              value={urlSelector}
              onChange={(e) => {
                setUrlSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
              }}
              placeholder="a"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">Uses href.</p>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Image selector</label>
            <input
              type="text"
              value={imageSelector}
              onChange={(e) => {
                setImageSelector(e.target.value);
                setSavedOk(false);
                setRunQueued(null);
              }}
              placeholder="img"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">Uses src.</p>
          </div>
        </div>

        {result && (
          <div className="space-y-3">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Fetch</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Method:</span>
                    <span className="font-mono">{result.fetch?.method || "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Status:</span>
                    <span className="font-mono">{result.fetch?.status_code ?? "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">HTML len:</span>
                    <span className="font-mono">{result.fetch?.html_len ?? "—"}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-400">Final URL:</span>
                    <span className="font-mono break-all">{result.fetch?.final_url || "—"}</span>
                  </div>
                </div>
              </div>

              <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Result</div>
                <div className="text-xs">
                  <div>
                    <span className="text-slate-400">Items found:</span>{" "}
                    <span className="font-mono">{result.items_found ?? 0}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Preview:</span>{" "}
                    <span className="font-mono">{preview.length}</span>
                  </div>
                </div>
              </div>
            </div>

            {(result.errors || []).length > 0 && (
              <div className="rounded border border-slate-800 bg-slate-950 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Errors</div>
                <ul className="list-disc pl-5 space-y-1 text-xs text-slate-400">
                  {(result.errors || []).map((msg, idx) => (
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
                  {preview.length === 0 ? (
                    <TR>
                      <TD colSpan={4} className="text-slate-500">
                        No preview items.
                      </TD>
                    </TR>
                  ) : (
                    preview.map((row, idx) => (
                      <TR key={idx}>
                        <TD className="text-xs">{row.title || "—"}</TD>
                        <TD className="text-xs">{row.price || "—"}</TD>
                        <TD className="text-xs break-all">{row.url || "—"}</TD>
                        <TD className="text-xs break-all">{row.image || "—"}</TD>
                      </TR>
                    ))
                  )}
                </TBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
