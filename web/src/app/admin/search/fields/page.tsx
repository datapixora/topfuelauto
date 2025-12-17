"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, authHeaders } from "../../../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "../../../../components/ui/table";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";

type SearchFieldRow = {
  id: number;
  key: string;
  label: string;
  data_type: "integer" | "string" | "decimal" | "boolean" | "date" | string;
  storage: "core" | "extra" | string;
  enabled: boolean;
  filterable: boolean;
  sortable: boolean;
  visible_in_search: boolean;
  visible_in_results: boolean;
  ui_widget?: string | null;
  source_aliases: string[];
  normalization: Record<string, any>;
  created_at?: string;
  updated_at?: string;
};

type ToastItem = {
  id: string;
  kind: "success" | "error";
  message: string;
};

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-lg border border-slate-800 bg-slate-900 shadow-xl relative">
        <button className="absolute right-3 top-3 text-slate-400" onClick={onClose} aria-label="Close">
          x
        </button>
        <div className="border-b border-slate-800 px-4 py-3">
          <div className="text-lg font-semibold">{title}</div>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

function ToastStack({ toasts, dismiss }: { toasts: ToastItem[]; dismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed right-5 top-5 z-50 flex w-[360px] flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`rounded-md border px-3 py-2 text-sm shadow ${
            t.kind === "success"
              ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-50"
              : "border-red-500/60 bg-red-500/10 text-red-100"
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="leading-relaxed">{t.message}</div>
            <button className="text-slate-400 hover:text-slate-200" onClick={() => dismiss(t.id)}>
              x
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

const DATA_TYPES = [
  { value: "string", label: "String" },
  { value: "integer", label: "Integer" },
  { value: "decimal", label: "Decimal" },
  { value: "boolean", label: "Boolean" },
  { value: "date", label: "Date" },
];

const STORAGES = [
  { value: "core", label: "Core (column)" },
  { value: "extra", label: "Extra (JSON)" },
];

export default function AdminSearchFieldsPage() {
  const [rows, setRows] = useState<SearchFieldRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyIds, setBusyIds] = useState<Record<number, boolean>>({});
  const [addOpen, setAddOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const [form, setForm] = useState({
    key: "",
    label: "",
    data_type: "string",
    storage: "extra",
    ui_widget: "",
    source_aliases: "",
    normalization: "",
  });

  const auth = useMemo(() => authHeaders(), []);

  const pushToast = (kind: ToastItem["kind"], message: string) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((prev) => [...prev, { id, kind, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 2600);
  };

  const dismissToast = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/search/fields`, { headers: { ...auth } });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Failed to load (${res.status}) ${txt}`.trim());
      }
      const json = (await res.json()) as SearchFieldRow[];
      setRows(Array.isArray(json) ? json : []);
    } catch (e: any) {
      pushToast("error", e?.message || "Failed to load search fields");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const setBusy = (id: number, value: boolean) =>
    setBusyIds((prev) => {
      const next = { ...prev };
      if (value) next[id] = true;
      else delete next[id];
      return next;
    });

  const patchRow = async (id: number, patch: Partial<SearchFieldRow>) => {
    setBusy(id, true);
    try {
      const res = await fetch(`${API_BASE}/admin/search/fields/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...auth },
        body: JSON.stringify(patch),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Update failed (${res.status}) ${txt}`.trim());
      }
      const updated = (await res.json()) as SearchFieldRow;
      setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...updated } : r)));
      pushToast("success", `Updated "${updated.key}"`);
    } catch (e: any) {
      pushToast("error", e?.message || "Update failed");
      await load();
    } finally {
      setBusy(id, false);
    }
  };

  const parseAliases = (text: string) =>
    text
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean);

  const createField = async () => {
    setCreating(true);
    try {
      let normalizationObj: Record<string, any> = {};
      const normText = form.normalization.trim();
      if (normText) {
        normalizationObj = JSON.parse(normText);
        if (normalizationObj === null || typeof normalizationObj !== "object" || Array.isArray(normalizationObj)) {
          throw new Error("Normalization must be a JSON object");
        }
      }

      const payload = {
        key: form.key.trim(),
        label: form.label.trim(),
        data_type: form.data_type,
        storage: form.storage,
        ui_widget: form.ui_widget.trim() || null,
        source_aliases: parseAliases(form.source_aliases),
        normalization: normalizationObj,
      };

      const res = await fetch(`${API_BASE}/admin/search/fields`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...auth },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Create failed (${res.status}) ${txt}`.trim());
      }
      const created = (await res.json()) as SearchFieldRow;
      pushToast("success", `Created "${created.key}"`);
      setAddOpen(false);
      setForm({
        key: "",
        label: "",
        data_type: "string",
        storage: "extra",
        ui_widget: "",
        source_aliases: "",
        normalization: "",
      });
      await load();
    } catch (e: any) {
      pushToast("error", e?.message || "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const deleteField = async (row: SearchFieldRow) => {
    const ok = window.confirm(
      `Delete field "${row.key}"?\n\nThis does NOT delete existing data from listings.extra. Consider disabling instead.`
    );
    if (!ok) return;

    setDeletingId(row.id);
    try {
      const res = await fetch(`${API_BASE}/admin/search/fields/${row.id}`, {
        method: "DELETE",
        headers: { ...auth },
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Delete failed (${res.status}) ${txt}`.trim());
      }
      pushToast("success", `Deleted "${row.key}"`);
      await load();
    } catch (e: any) {
      pushToast("error", e?.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <ToastStack toasts={toasts} dismiss={dismissToast} />

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Search Fields</CardTitle>
            <div className="text-xs text-slate-400">
              Registry of dynamic fields used for search filters, result columns, and CSV mapping.
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={load} disabled={loading}>
              Reload
            </Button>
            <Button onClick={() => setAddOpen(true)}>Add field</Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading && <div className="text-slate-400 text-sm mb-3">Loading...</div>}
          <div className="overflow-x-auto">
            <Table className="min-w-[980px]">
              <THead>
                <TR>
                  <TH>Key</TH>
                  <TH>Label</TH>
                  <TH>Type</TH>
                  <TH>Storage</TH>
                  <TH className="text-center">Enabled</TH>
                  <TH className="text-center">Filter</TH>
                  <TH className="text-center">Sort</TH>
                  <TH className="text-center">In search</TH>
                  <TH className="text-center">In results</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {rows.map((r) => {
                  const busy = Boolean(busyIds[r.id]) || deletingId === r.id;
                  return (
                    <TR key={r.id}>
                      <TD className="font-mono text-xs whitespace-nowrap">{r.key}</TD>
                      <TD className="max-w-[260px] truncate" title={r.label}>
                        {r.label}
                      </TD>
                      <TD className="whitespace-nowrap">{r.data_type}</TD>
                      <TD className="whitespace-nowrap">{r.storage}</TD>
                      <TD className="text-center">
                        <input
                          type="checkbox"
                          checked={r.enabled}
                          disabled={busy}
                          onChange={(e) => patchRow(r.id, { enabled: e.target.checked })}
                        />
                      </TD>
                      <TD className="text-center">
                        <input
                          type="checkbox"
                          checked={r.filterable}
                          disabled={busy}
                          onChange={(e) => patchRow(r.id, { filterable: e.target.checked })}
                        />
                      </TD>
                      <TD className="text-center">
                        <input
                          type="checkbox"
                          checked={r.sortable}
                          disabled={busy}
                          onChange={(e) => patchRow(r.id, { sortable: e.target.checked })}
                        />
                      </TD>
                      <TD className="text-center">
                        <input
                          type="checkbox"
                          checked={r.visible_in_search}
                          disabled={busy}
                          onChange={(e) => patchRow(r.id, { visible_in_search: e.target.checked })}
                        />
                      </TD>
                      <TD className="text-center">
                        <input
                          type="checkbox"
                          checked={r.visible_in_results}
                          disabled={busy}
                          onChange={(e) => patchRow(r.id, { visible_in_results: e.target.checked })}
                        />
                      </TD>
                      <TD className="text-right whitespace-nowrap">
                        <Button
                          variant="ghost"
                          className="border border-red-500/30 text-red-200 hover:bg-red-500/10"
                          onClick={() => deleteField(r)}
                          disabled={busy}
                        >
                          {deletingId === r.id ? "Deleting..." : "Delete"}
                        </Button>
                      </TD>
                    </TR>
                  );
                })}

                {!loading && rows.length === 0 && (
                  <TR>
                    <TD colSpan={10} className="text-slate-500 text-sm py-6 text-center">
                      No search fields configured yet.
                    </TD>
                  </TR>
                )}
              </TBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {addOpen && (
        <Modal title="Add Search Field" onClose={() => (creating ? null : setAddOpen(false))}>
          <div className="space-y-4 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1">
                <div className="text-slate-200">Key</div>
                <Input
                  value={form.key}
                  onChange={(e) => setForm({ ...form, key: e.target.value })}
                  placeholder="fuel_type"
                />
                <div className="text-xs text-slate-500">Lowercase letters, numbers, underscores.</div>
              </label>
              <label className="space-y-1">
                <div className="text-slate-200">Label</div>
                <Input
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  placeholder="Fuel Type"
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <label className="space-y-1">
                <div className="text-slate-200">Data type</div>
                <select
                  className="h-10 w-full rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-100"
                  value={form.data_type}
                  onChange={(e) => setForm({ ...form, data_type: e.target.value })}
                >
                  {DATA_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <div className="text-slate-200">Storage</div>
                <select
                  className="h-10 w-full rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-100"
                  value={form.storage}
                  onChange={(e) => setForm({ ...form, storage: e.target.value })}
                >
                  {STORAGES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <div className="text-slate-200">UI widget (optional)</div>
                <Input
                  value={form.ui_widget}
                  onChange={(e) => setForm({ ...form, ui_widget: e.target.value })}
                  placeholder="select / range / text"
                />
              </label>
            </div>

            <label className="space-y-1">
              <div className="text-slate-200">Source aliases (comma-separated)</div>
              <Input
                value={form.source_aliases}
                onChange={(e) => setForm({ ...form, source_aliases: e.target.value })}
                placeholder="fuel, fuelType, fuel_type"
              />
              <div className="text-xs text-slate-500">Used for CSV import mapping and other source adapters.</div>
            </label>

            <label className="space-y-1">
              <div className="text-slate-200">Normalization (optional JSON)</div>
              <textarea
                className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-xs min-h-[120px] text-slate-100"
                value={form.normalization}
                onChange={(e) => setForm({ ...form, normalization: e.target.value })}
                placeholder={'{ "trim": true, "lowercase": true }'}
              />
            </label>

            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setAddOpen(false)} disabled={creating}>
                Cancel
              </Button>
              <Button onClick={createField} disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

