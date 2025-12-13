"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SearchBar() {
  const [query, setQuery] = useState("Nissan GT-R 2005");
  const router = useRouter();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 text-slate-100"
        placeholder="Search make, model, year..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button
        type="submit"
        className="px-4 py-3 rounded-lg bg-brand-accent text-slate-950 font-semibold"
      >
        Search
      </button>
    </form>
  );
}