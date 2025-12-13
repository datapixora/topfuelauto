"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getListing, requestBid } from "../../../lib/api";
import { Listing } from "../../../lib/types";
import VinPanel from "../../../components/VinPanel";
import { getToken } from "../../../lib/auth";

export default function ListingPage() {
  const params = useParams();
  const id = params?.id as string;
  const [listing, setListing] = useState<Listing | null>(null);
  const [form, setForm] = useState({ destination_country: "USA", full_name: "", phone: "", max_bid: "" });
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getListing(id).then(setListing).catch(() => setStatus("Unable to load listing"));
  }, [id]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!getToken()) {
      setStatus("Please login to request a bid.");
      return;
    }
    try {
      await requestBid({
        listing_id: Number(id),
        destination_country: form.destination_country,
        full_name: form.full_name,
        phone: form.phone,
        max_bid: form.max_bid ? Number(form.max_bid) : undefined,
      });
      setStatus("Bid request sent");
    } catch (e) {
      setStatus("Failed to send bid");
    }
  };

  if (!listing) return <div className="text-slate-400">Loading...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="md:col-span-2 space-y-4">
        <div className="card">
          <div className="text-2xl font-bold">{listing.title}</div>
          <div className="text-slate-400">
            {listing.vehicle.year} {listing.vehicle.make} {listing.vehicle.model} {listing.vehicle.trim ?? ""}
          </div>
          <div className="mt-3 text-lg">
            {listing.price ? `${listing.currency ?? "USD"} ${Number(listing.price).toLocaleString()}` : "Contact"}
          </div>
          <div className="text-slate-400 text-sm">{listing.location}</div>
        </div>
        <VinPanel />
      </div>
      <div className="space-y-3">
        <div className="card">
          <div className="font-semibold mb-2">Request a broker bid</div>
          <form className="space-y-2" onSubmit={onSubmit}>
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
              placeholder="Full name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              required
            />
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
              placeholder="Destination country"
              value={form.destination_country}
              onChange={(e) => setForm({ ...form, destination_country: e.target.value })}
              required
            />
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
              placeholder="Max bid (optional)"
              value={form.max_bid}
              onChange={(e) => setForm({ ...form, max_bid: e.target.value })}
            />
            <button type="submit" className="w-full bg-brand-accent text-slate-950 font-semibold rounded px-3 py-2">
              Send request
            </button>
          </form>
          {status && <div className="text-xs text-slate-400 mt-2">{status}</div>}
        </div>
      </div>
    </div>
  );
}
