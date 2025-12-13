"use client";

import { useState, useEffect } from "react";

type FiltersProps = {
  value: Record<string, string | number | undefined>;
  onChange: (next: Record<string, string | number | undefined>) => void;
};

export default function Filters({ value, onChange }: FiltersProps) {
  const [local, setLocal] = useState(value);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  const update = (key: string, val: string) => {
    const next = { ...local, [key]: val };
    setLocal(next);
    onChange(next);
  };

  return (
    <div className="card space-y-3">
      <div className="text-sm uppercase text-slate-400 tracking-wide">Filters</div>
      <div className="grid grid-cols-2 gap-3">
        <input
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Year min"
          value={local.year_min ?? ""}
          onChange={(e) => update("year_min", e.target.value)}
        />
        <input
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Year max"
          value={local.year_max ?? ""}
          onChange={(e) => update("year_max", e.target.value)}
        />
        <input
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Price min"
          value={local.price_min ?? ""}
          onChange={(e) => update("price_min", e.target.value)}
        />
        <input
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Price max"
          value={local.price_max ?? ""}
          onChange={(e) => update("price_max", e.target.value)}
        />
        <input
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2 col-span-2"
          placeholder="Location"
          value={local.location ?? ""}
          onChange={(e) => update("location", e.target.value)}
        />
      </div>
    </div>
  );
}