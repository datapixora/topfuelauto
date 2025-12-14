import { getToken } from "./auth";
import { Listing, SearchResult, SearchResponse, TokenResponse, QuotaInfo } from "./types";

const RAW_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

const normalizeBase = (base: string) => {
  if (!base) return "";
  const trimmed = base.replace(/\/+$/, "");
  // If base already ends with /api/v1, keep it; else append once.
  if (trimmed.endsWith("/api/v1")) return trimmed;
  return `${trimmed}/api/v1`;
};

export const API_BASE = normalizeBase(RAW_BASE);

const requireBase = () => {
  if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is missing. Set it to your API origin (e.g. https://api.example.com).");
  }
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
  const res = await fetch(url(`/search?${qs.toString()}`), { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

type QuotaError = {
  kind: "quota";
  detail: string;
  limit: number | null;
  used: number | null;
  remaining: number | null;
  reset_at?: string | null;
};

const parseQuotaError = async (res: Response): Promise<QuotaError | null> => {
  try {
    const payload = await res.json();
    if (payload?.code === "quota_exceeded") {
      return {
        kind: "quota",
        detail: payload?.detail || "Daily search limit reached.",
        limit: payload?.limit ?? null,
        used: payload?.used ?? null,
        remaining: payload?.remaining ?? null,
        reset_at: payload?.reset_at ?? null,
      };
    }
  } catch {
    /* ignore */
  }
  return null;
};

export async function searchMarketplace(params: Record<string, string | number | undefined>): Promise<SearchResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, String(v));
  });
  const res = await fetch(url(`/search?${qs.toString()}`), { headers: { ...authHeaders() } });
  if (res.ok) {
    return res.json();
  }
  if (res.status === 429) {
    const quota = await parseQuotaError(res);
    const err = new Error(quota?.detail || "Daily search limit reached.");
    (err as any).quota = quota;
    throw err;
  }
  throw new Error(`Search failed (${res.status})`);
}

export async function getListing(id: string | number): Promise<Listing> {
  const res = await fetch(url(`/listings/${id}`));
  if (!res.ok) throw new Error("Listing not found");
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const payload = JSON.stringify({ email, password });
  const headers = { "Content-Type": "application/json" };
  const candidates = ["/auth/login", "/auth/token"];

  let lastError: string | undefined;

  for (const path of candidates) {
    const res = await fetch(url(path), {
      method: "POST",
      headers,
      body: payload,
    });

    if (res.ok) return res.json();

    const detail = await res
      .json()
      .then((data) => (typeof data?.detail === "string" ? data.detail : null))
      .catch(() => null);

    lastError = detail || `Login failed with status ${res.status}`;

    if (res.status === 404) {
      continue;
    } else {
      break;
    }
  }

  throw new Error(lastError || "Login failed");
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

export async function getQuota(): Promise<QuotaInfo> {
  const res = await fetch(url("/auth/me/quota"), {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Unable to load quota");
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

const inFlight = new Map<string, Promise<any>>();

export async function apiGet<T = any>(path: string, init?: RequestInit): Promise<T> {
  const absolute = path.startsWith("http") ? path : url(path);
  const method = (init?.method || "GET").toUpperCase();
  const key = `${method} ${absolute}`;

  if (inFlight.has(key)) {
    return inFlight.get(key) as Promise<T>;
  }

  const promise = fetch(absolute, {
    ...init,
    method,
    headers: { ...(init?.headers || {}), ...authHeaders() },
  }).then(async (res) => {
    inFlight.delete(key);
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    return res.json();
  }).catch((err) => {
    inFlight.delete(key);
    throw err;
  });

  inFlight.set(key, promise);
  return promise;
}
