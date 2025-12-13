import { getToken } from "./auth";
import { Listing, SearchResult, TokenResponse } from "./types";

const RAW_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "";

const normalizeBase = (base: string) => {
  if (!base) return "";
  const trimmed = base.replace(/\/+$/, "");
  // If base already ends with /api/v1, keep it; else append once.
  if (trimmed.endsWith("/api/v1")) return trimmed;
  return `${trimmed}/api/v1`;
};

export const API_BASE = normalizeBase(RAW_BASE);

const requireBase = () => {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");
  return API_BASE;
};

const url = (path: string) => {
  const base = requireBase();
  return `${base}${path.startsWith("/") ? "" : "/"}${path}`;
};

export const authHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function searchVehicles(params: Record<string, string | number | undefined>): Promise<SearchResult[]> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, String(v));
  });
  const res = await fetch(url(`/search?${qs.toString()}`));
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function getListing(id: string | number): Promise<Listing> {
  const res = await fetch(url(`/listings/${id}`));
  if (!res.ok) throw new Error("Listing not found");
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(url("/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}

export async function signup(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(url("/auth/signup"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Signup failed");
  return res.json();
}

export async function requestBid(payload: {
  listing_id: number;
  max_bid?: number;
  destination_country: string;
  full_name: string;
  phone: string;
}) {
  const res = await fetch(url("/broker/request-bid"), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Request failed");
  return res.json();
}

export async function decodeVin(vin: string) {
  const res = await fetch(url(`/vin/decode?vin=${encodeURIComponent(vin)}`));
  if (!res.ok) throw new Error("VIN decode failed");
  return res.json();
}
