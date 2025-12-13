import Link from "next/link";
import { SearchResult } from "../lib/types";
import ProBadge from "./ProBadge";

export default function ListingCard({ result }: { result: SearchResult }) {
  return (
    <div className="card flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">{result.title}</div>
          <div className="text-slate-400 text-sm">
            {result.year} {result.make} {result.model} {result.trim ?? ""}
          </div>
        </div>
        <ProBadge show={!!result.risk_flags?.length} label="Pro" />
      </div>
      <div className="flex items-center justify-between text-sm text-slate-300">
        <div>
          {result.price ? `${result.currency ?? "USD"} ${Number(result.price).toLocaleString()}` : "Ask"}
        </div>
        <div>{result.location}</div>
      </div>
      <div className="flex justify-between items-center mt-2">
        <Link href={`/listing/${result.listing_id}`} className="text-brand-accent font-semibold">
          View details
        </Link>
        {result.score !== undefined && (
          <span className="text-xs text-slate-500">score {result.score?.toFixed(2)}</span>
        )}
      </div>
    </div>
  );
}