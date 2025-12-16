"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { listStagedListings, approveStagedListing, rejectStagedListing, bulkApproveStagedListings, bulkRejectStagedListings } from "../../../../lib/api";
import { StagedListing } from "../../../../lib/types";

export default function StagedListingsPage() {
  const [listings, setListings] = useState<StagedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [actionLoading, setActionLoading] = useState(false);

  const loadListings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listStagedListings();
      setListings(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadListings();
  }, []);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(listings.map((l) => l.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: number, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleApprove = async (id: number) => {
    if (!confirm("Approve this listing? It will be merged to the main catalog.")) return;

    setActionLoading(true);
    try {
      await approveStagedListing(id);
      await loadListings();
      setSelectedIds(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: number) => {
    if (!confirm("Reject this listing? It will be permanently deleted.")) return;

    setActionLoading(true);
    try {
      await rejectStagedListing(id);
      await loadListings();
      setSelectedIds(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Approve ${selectedIds.size} listings? They will be merged to the main catalog.`)) return;

    setActionLoading(true);
    try {
      await bulkApproveStagedListings(Array.from(selectedIds));
      await loadListings();
      setSelectedIds(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkReject = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Reject ${selectedIds.size} listings? They will be permanently deleted.`)) return;

    setActionLoading(true);
    try {
      await bulkRejectStagedListings(Array.from(selectedIds));
      await loadListings();
      setSelectedIds(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Staging Queue</h1>
          <p className="text-sm text-slate-400">Review and approve scraped listings</p>
        </div>
        {selectedIds.size > 0 && (
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={handleBulkApprove}
              disabled={actionLoading}
              className="text-green-400 hover:text-green-300"
            >
              Approve {selectedIds.size} Selected
            </Button>
            <Button
              variant="ghost"
              onClick={handleBulkReject}
              disabled={actionLoading}
              className="text-red-400 hover:text-red-300"
            >
              Reject {selectedIds.size} Selected
            </Button>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {loading && <div className="text-slate-400 text-sm">Loading staged listings...</div>}

      {!loading && listings.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          <div className="text-lg mb-2">No staged listings</div>
          <div className="text-sm">Listings will appear here after scraping runs</div>
        </div>
      )}

      {listings.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 p-3 bg-slate-800/50 rounded">
            <input
              type="checkbox"
              checked={selectedIds.size === listings.length}
              onChange={(e) => handleSelectAll(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm text-slate-400">
              Select All ({listings.length} listings)
            </span>
          </div>

          <div className="space-y-3">
            {listings.map((listing) => (
              <Card key={listing.id} className="relative">
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(listing.id)}
                      onChange={(e) => handleSelectOne(listing.id, e.target.checked)}
                      className="w-4 h-4 mt-1"
                    />
                    <div className="flex-1">
                      <CardTitle className="text-lg">{listing.title || "Untitled"}</CardTitle>
                      <div className="text-xs text-slate-500 font-mono mt-1">
                        #{listing.id} • {listing.source_key}
                        {listing.source_listing_id && ` • Source ID: ${listing.source_listing_id}`}
                      </div>
                    </div>
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        listing.status === "active"
                          ? "bg-green-900/30 text-green-400"
                          : listing.status === "ended"
                          ? "bg-slate-700 text-slate-400"
                          : "bg-yellow-900/30 text-yellow-400"
                      }`}
                    >
                      {listing.status}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    {listing.year && (
                      <div>
                        <span className="text-slate-400">Year:</span>{" "}
                        <span className="font-medium">{listing.year}</span>
                      </div>
                    )}
                    {listing.make && (
                      <div>
                        <span className="text-slate-400">Make:</span>{" "}
                        <span className="font-medium">{listing.make}</span>
                      </div>
                    )}
                    {listing.model && (
                      <div>
                        <span className="text-slate-400">Model:</span>{" "}
                        <span className="font-medium">{listing.model}</span>
                      </div>
                    )}
                    {listing.price_amount && (
                      <div>
                        <span className="text-slate-400">Price:</span>{" "}
                        <span className="font-medium">
                          {listing.currency} {listing.price_amount.toLocaleString()}
                        </span>
                      </div>
                    )}
                    {listing.odometer_value && (
                      <div>
                        <span className="text-slate-400">Odometer:</span>{" "}
                        <span className="font-medium">{listing.odometer_value.toLocaleString()}</span>
                      </div>
                    )}
                    {listing.location && (
                      <div>
                        <span className="text-slate-400">Location:</span>{" "}
                        <span className="font-medium">{listing.location}</span>
                      </div>
                    )}
                    {listing.listed_at && (
                      <div>
                        <span className="text-slate-400">Listed:</span>{" "}
                        <span className="font-medium text-xs">{formatDate(listing.listed_at)}</span>
                      </div>
                    )}
                    {listing.fetched_at && (
                      <div>
                        <span className="text-slate-400">Fetched:</span>{" "}
                        <span className="font-medium text-xs">{formatDate(listing.fetched_at)}</span>
                      </div>
                    )}
                  </div>

                  {listing.attributes && listing.attributes.length > 0 && (
                    <details className="text-sm">
                      <summary className="text-slate-400 cursor-pointer hover:text-slate-300">
                        Attributes ({listing.attributes.length})
                      </summary>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2 pl-4">
                        {listing.attributes.map((attr) => (
                          <div key={attr.id} className="text-xs">
                            <span className="text-slate-500">{attr.key}:</span>{" "}
                            <span className="font-medium">
                              {attr.value_text || attr.value_num || (attr.value_bool !== null ? String(attr.value_bool) : "N/A")}
                              {attr.unit && ` ${attr.unit}`}
                            </span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  <div className="flex gap-2 pt-2 border-t border-slate-800">
                    <a
                      href={listing.canonical_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 underline flex-1"
                    >
                      View Source →
                    </a>
                    <Button
                      variant="ghost"
                      onClick={() => handleApprove(listing.id)}
                      disabled={actionLoading}
                      className="text-green-400 hover:text-green-300 text-xs"
                    >
                      Approve
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => handleReject(listing.id)}
                      disabled={actionLoading}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Reject
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
