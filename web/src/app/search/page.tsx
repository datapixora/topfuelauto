"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import TopNav from "../../components/TopNav";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { searchMarketplace } from "../../lib/api";
import { getToken } from "../../lib/auth";
import { SearchItem } from "../../lib/types";

const DEFAULT_PAGE_SIZE = 10;
const FREE_SEARCH_KEY = "tfa_free_search_count";

type FormState = {
  q: string;
  make?: string;
  model?: string;
  year_min?: string;
  year_max?: string;
  price_min?: string;
  price_max?: string;
};

function formatPrice(price?: number | null, currency?: string | null) {
  if (price === undefined || price === null) return "—";
  const cur = currency || "USD";
  return `${cur} ${Number(price).toLocaleString()}`;
}

function canSearchWithoutToken(): boolean {
  if (getToken()) return true;
  if (typeof window === "undefined") return true;
  const today = new Date().toISOString().slice(0, 10);
  const raw = localStorage.getItem(FREE_SEARCH_KEY);
  if (!raw) return true;
  try {
    const parsed = JSON.parse(raw) as { date: string; count: number };
    if (parsed.date !== today) return true;
    return parsed.count < 1;
  } catch {
    return true;
  }
}

function incrementFreeSearch() {
  if (typeof window === "undefined") return;
  const today = new Date().toISOString().slice(0, 10);
  const raw = localStorage.getItem(FREE_SEARCH_KEY);
  let count = 0;
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as { date: string; count: number };
      if (parsed.date === today) {
        count = parsed.count;
      }
    } catch {
      /* ignore */
    }
  }
  localStorage.setItem(FREE_SEARCH_KEY, JSON.stringify({ date: today, count: count + 1 }));
}

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") || "";

  const [form, setForm] = useState<FormState>({ q: initialQ });
  const [items, setItems] = useState<SearchItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  const doSearch = async (targetPage: number, skipGate = false) => {
    if (!skipGate && !getToken() && !canSearchWithoutToken()) {
      router.push("/login?next=/search");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await searchMarketplace({
        q: form.q,
        make: form.make,
        model: form.model,
        year_min: form.year_min,
        year_max: form.year_max,
        price_min: form.price_min,
        price_max: form.price_max,
        page: targetPage,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
      setPage(targetPage);
      if (!getToken()) {
        incrementFreeSearch();
      }
    } catch (err: any) {
      setError(err?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    void doSearch(1);
  };

  const onPageChange = (delta: number) => {
    const nextPage = page + delta;
    if (nextPage < 1 || nextPage > totalPages) return;
    void doSearch(nextPage);
  };

  return (
    <div className="space-y-8">
      <TopNav />

      <Card>
        <CardHeader>
          <CardTitle>Search vehicles</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={onSubmit}>
            <div className="md:col-span-3">
              <Input
                required
                placeholder="Search (e.g. Nissan GT-R)"
                value={form.q}
                onChange={(e) => setForm({ ...form, q: e.target.value })}
              />
            </div>
            <Input
              placeholder="Make"
              value={form.make || ""}
              onChange={(e) => setForm({ ...form, make: e.target.value })}
            />
            <Input
              placeholder="Model"
              value={form.model || ""}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
            />
            <div className="flex gap-2">
              <Input
                placeholder="Year min"
                value={form.year_min || ""}
                onChange={(e) => setForm({ ...form, year_min: e.target.value })}
              />
              <Input
                placeholder="Year max"
                value={form.year_max || ""}
                onChange={(e) => setForm({ ...form, year_max: e.target.value })}
              />
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Price min"
                value={form.price_min || ""}
                onChange={(e) => setForm({ ...form, price_min: e.target.value })}
              />
              <Input
                placeholder="Price max"
                value={form.price_max || ""}
                onChange={(e) => setForm({ ...form, price_max: e.target.value })}
              />
            </div>
            <div className="md:col-span-3 flex items-center gap-3">
              <Button type="submit" disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </Button>
              {!getToken() && (
                <span className="text-xs text-slate-400">
                  Free preview: 1 search while logged out. Sign in for more.
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {error && <div className="text-red-300 text-sm">{error}</div>}

      {!loading && items.length === 0 && !error && (
        <div className="text-slate-400 text-sm">No results yet. Try a different query.</div>
      )}

      {loading && <div className="text-slate-300">Loading...</div>}

      <div className="grid gap-4">
        {items.map((item) => (
          <Card key={item.id}>
            <CardContent className="flex flex-col md:flex-row gap-4 py-4">
              {item.thumbnail_url && (
                <img src={item.thumbnail_url} alt={item.title} className="h-24 w-36 object-cover rounded-md" />
              )}
              <div className="flex-1 space-y-1">
                <div className="text-sm uppercase text-slate-400">{item.source || "source"}</div>
                <div className="text-lg font-semibold">{item.title}</div>
                <div className="text-slate-300 text-sm">
                  {item.year || "—"} • {item.make || "—"} {item.model || ""}
                </div>
                <div className="text-slate-200 font-semibold">{formatPrice(item.price, item.currency)}</div>
                <div className="text-slate-400 text-sm">{item.location || "—"}</div>
                {item.url && (
                  <a
                    className="text-brand-accent text-sm hover:underline"
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View source
                  </a>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {items.length > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-300">
          <div>
            Page {page} of {totalPages} • {total} results
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" disabled={page <= 1} onClick={() => onPageChange(-1)}>
              Previous
            </Button>
            <Button variant="ghost" disabled={page >= totalPages} onClick={() => onPageChange(1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-slate-400">Loading search...</div>}>
      <SearchContent />
    </Suspense>
  );
}
