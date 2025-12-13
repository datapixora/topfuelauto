"use client";

import { useState } from "react";
import { decodeVin } from "../lib/api";

export default function VinPanel() {
  const [vin, setVin] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const onDecode = async () => {
    if (!vin) return;
    setLoading(true);
    try {
      const data = await decodeVin(vin);
      setResult(data);
    } catch (e) {
      setResult({ status: "ERROR", message: "Failed to decode" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-semibold">VIN tools</div>
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded bg-slate-800 border border-slate-700 px-3 py-2"
          placeholder="Enter VIN"
          value={vin}
          onChange={(e) => setVin(e.target.value)}
        />
        <button
          onClick={onDecode}
          className="px-4 py-2 rounded bg-brand-accent text-slate-950 font-semibold"
          disabled={loading}
        >
          {loading ? "Decoding..." : "Decode"}
        </button>
      </div>
      {result && (
        <div className="text-sm text-slate-300 whitespace-pre-wrap break-words">
          {result.status}: {result.message || result.results?.Model || ""}
        </div>
      )}
    </div>
  );
}