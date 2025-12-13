import Link from "next/link";
import SearchBar from "../components/SearchBar";
import HomeStatus from "../components/HomeStatus";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="card">
        <div className="text-3xl font-bold mb-1">TopFuel Auto Web</div>
        <p className="text-slate-300 mb-4">
          Search-first marketplace. Normalized listings, fuzzy matching, and VIN tools. Try a hero search like "Nissan GT-R 2005".
        </p>
        <SearchBar />
      </div>

      <HomeStatus />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="font-semibold">Search-first</div>
          <p className="text-slate-400 text-sm">Postgres full-text + trigram ranking keeps relevance high.</p>
        </div>
        <div className="card">
          <div className="font-semibold">Broker bids</div>
          <p className="text-slate-400 text-sm">Request bids on auction cars directly to brokers.</p>
        </div>
        <div className="card">
          <div className="font-semibold">Pro VIN history</div>
          <p className="text-slate-400 text-sm">VIN decode for everyone; history gated for Pros.</p>
        </div>
      </div>
      <div className="flex gap-4">
        <Link href="/pricing" className="px-4 py-2 rounded bg-brand-accent text-slate-950 font-semibold">
          View Pricing
        </Link>
        <Link href="/search" className="px-4 py-2 rounded border border-slate-700 text-slate-100">
          Open search
        </Link>
      </div>
    </div>
  );
}
