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
}) {
  const router = useRouter();

  const detectedStrategy = useMemo(() => {
    const s = props.initialSettingsJson?.detected_strategy;
    return typeof s === "string" ? s : "";
  }, [props.initialSettingsJson]);

  const initialTestUrl = useMemo(() => {
    const targets = props.initialSettingsJson?.targets;
    const val = targets?.test_url;
    return typeof val === "string" ? val : "";
  }, [props.initialSettingsJson]);

  const initialExtract = useMemo(
    () => normalizeExtract(props.initialSettingsJson?.extract || {}),
    [props.initialSettingsJson]
  );

  const [testUrl, setTestUrl] = useState(initialTestUrl);
  const [itemSelector, setItemSelector] = useState(initialExtract.list.item_selector || "");
  const [nextPageSelector, setNextPageSelector] = useState(initialExtract.list.next_page_selector || "");
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

  useEffect(() => {
    setTestUrl(initialTestUrl);
    const next = normalizeExtract(props.initialSettingsJson?.extract || {});
    setItemSelector(next.list.item_selector || "");
    setNextPageSelector(next.list.next_page_selector || "");
    setTitleSelector((next.fields?.title?.selector as string) || "");
    setPriceSelector((next.fields?.price?.selector as string) || "");
    setUrlSelector((next.fields?.url?.selector as string) || "");
    setImageSelector((next.fields?.image?.selector as string) || "");
    setSavedOk(false);
    setRunQueued(null);
  }, [props.initialSettingsJson, initialTestUrl]);

  const buildConfig = (): ExtractConfig => ({
    strategy: "generic_html_list",
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
    const fromInput = testUrl.trim();
    if (fromInput) return fromInput;
    const fromFetch = result?.fetch?.final_url;
    return typeof fromFetch === "string" ? fromFetch : "";
  }, [testUrl, result?.fetch?.final_url]);

  const canSave = (preview.length > 0 || !!testUrl.trim()) && !!saveUrl;

  const handleTest = async () => {
    setTesting(true);
    setError(null);
    setSavedOk(false);
    setRunQueued(null);
    try {
      const res = (await testExtractDataSource(props.sourceId, {
        url: testUrl.trim() || undefined,
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
      setError("Missing URL. Provide a Test URL or run Test Extract first.");
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
      setTestUrl(saveUrl);
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
        {detectedStrategy && detectedStrategy !== "generic_html_list" && (
          <div className="text-xs text-slate-500">
            Detected strategy is <span className="font-mono">{detectedStrategy}</span>. This template is designed for{" "}
            <span className="font-mono">generic_html_list</span>, but you can configure it manually.
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

        <div>
          <label className="block text-xs uppercase tracking-wide text-slate-400 mb-1">Test URL</label>
          <input
            type="text"
            value={testUrl}
            onChange={(e) => {
              setTestUrl(e.target.value);
              setSavedOk(false);
              setRunQueued(null);
            }}
            placeholder="https://example.com/listings"
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
          />
          <p className="text-xs text-slate-500 mt-1">Used for Detect, Test Extract, and Save Template.</p>
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
