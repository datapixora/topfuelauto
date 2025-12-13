"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Filters from "../../components/Filters";
import ListingCard from "../../components/ListingCard";
import { searchVehicles } from "../../lib/api";
import { SearchResult } from "../../lib/types";

export default function SearchClient() {
  const params = useSearchParams();
  const initialQ = params.get("q") || "";
  const [query, setQuery] = useState(initialQ);
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({ q: initialQ });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const doSearch = async () => {
      if (!query) return;
      setLoading(true);
      try {
        const res = await searchVehicles({ ...filters, q: query });
        setResults(res);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    doSearch();
  }, [query, filters]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="md:col-span-1">
        <Filters value={filters} onChange={(next) => setFilters(next)} />
      </div>
      <div className="md:col-span-3 space-y-4">
        <div className="card flex items-center justify-between">
          <div className="font-semibold">Search results for "{query || "..."}"</div>
          {loading && <div className="text-xs text-slate-400">Loading…</div>}
        </div>
        {results.length === 0 && !loading && (
          <div className="text-slate-400">No results yet. Try searching for "Nissan GT-R 2005".</div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((r) => (
            <ListingCard key={r.listing_id} result={r} />
          ))}
        </div>
      </div>
    </div>
  );
}
