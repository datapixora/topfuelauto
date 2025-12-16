import { getToken, clearToken } from "./auth";
import {
  Listing,
  SearchResult,
  SearchResponse,
  TokenResponse,
  QuotaInfo,
  Plan,
  SavedSearchAlert,
  AlertMatch,
  NotificationItem,
  SearchJobResponse,
  WebCrawlProviderConfig,
} from "./types";

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

const redirectToLogin = () => {
  if (typeof window === "undefined") return;
  const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
  window.location.href = `/login?next=${next}`;
};

const handleUnauthorized = (shouldRedirect: boolean) => {
  clearToken();
  if (shouldRedirect && typeof window !== "undefined") {
    redirectToLogin();
  }
};

const authFetch = async (
  path: string,
  init?: RequestInit,
  opts?: { requireAuth?: boolean; redirectOn401?: boolean }
): Promise<Response> => {
  const requireAuth = opts?.requireAuth ?? true;
  const redirectOn401 = opts?.redirectOn401 ?? true;
  const absolute = path.startsWith("http") ? path : url(path);
  const token = getToken();

  if (requireAuth && !token) {
    handleUnauthorized(redirectOn401);
    throw new Error("Not authenticated");
  }

  const res = await fetch(absolute, {
    ...init,
    headers: { ...(init?.headers || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });

  if (res.status === 401) {
    handleUnauthorized(redirectOn401);
    throw new Error("Unauthorized");
  }

  return res;
};

export async function apiGet<T = any>(
  path: string,
  init?: RequestInit,
  opts?: { requireAuth?: boolean; redirectOn401?: boolean }
): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const res = await authFetch(path, { ...init, method }, opts);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

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

export async function getSearchJob(jobId: number): Promise<SearchJobResponse> {
  return apiGet<SearchJobResponse>(`/search/jobs/${jobId}`, undefined, { requireAuth: false, redirectOn401: false });
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
  const res = await authFetch("/auth/me/quota");
  if (!res.ok) throw new Error("Unable to load quota");
  return res.json();
}

export async function listPlans(): Promise<Plan[]> {
  const res = await fetch(url("/admin/plans/public"));
  if (!res.ok) throw new Error("Unable to load plans");
  const json = await res.json();
  return json.plans || [];
}

export async function startCheckout(planId: number, interval: "month" | "year"): Promise<string> {
  const res = await authFetch("/billing/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, interval }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    const code = detail?.code;
    if (code === "stripe_price_not_configured") {
      throw new Error("This plan is not configured for checkout yet.");
    }
    throw new Error(`Checkout failed (${res.status})`);
  }
  const json = await res.json();
  return json.checkout_url;
}

export async function fetchAssistCards() {
  return apiGet<{ cards: any[] }>("/assist/cards");
}

export async function listAssistCases() {
  return apiGet<{ cases: any[] }>("/assist/cases");
}

export async function createAssistCase(payload: any) {
  return apiPost("/assist/cases", payload);
}

export async function submitAssistCase(id: number) {
  return apiPost(`/assist/cases/${id}/submit`, {});
}

export async function cancelAssistCase(id: number) {
  return apiPost(`/assist/cases/${id}/cancel`, {});
}

export async function assistCaseDetail(id: number) {
  return apiGet<{ case: any; steps: any[]; artifacts: any[] }>(`/assist/cases/${id}`);
}

export async function listAlerts(): Promise<SavedSearchAlert[]> {
  const res = await apiGet<{ alerts: SavedSearchAlert[] }>("/alerts");
  return res.alerts || [];
}

export async function createAlert(payload: { name?: string; query: Record<string, any>; is_active?: boolean }) {
  return apiPost("/alerts", payload) as Promise<SavedSearchAlert>;
}

export async function alertDetail(
  id: number
): Promise<{ alert: SavedSearchAlert; matches: AlertMatch[] }> {
  return apiGet(`/alerts/${id}`);
}

export async function updateAlert(id: number, payload: { name?: string; is_active?: boolean }) {
  const res = await authFetch(`/alerts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Request failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function deleteAlert(id: number) {
  const res = await authFetch(`/alerts/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  return res.json();
}

export async function listNotifications(limit = 10): Promise<{ notifications: NotificationItem[]; unread_count: number }> {
  const res = await apiGet(`/notifications?limit=${limit}`);
  return res as { notifications: NotificationItem[]; unread_count: number };
}

export async function markNotificationRead(id: number) {
  return apiPost(`/notifications/${id}/read`, {});
}

export async function markAllNotificationsRead() {
  return apiPost("/notifications/read-all", {});
}

// Admin providers
export async function listProviderSettings() {
  return apiGet<{ key: string; enabled: boolean; priority: number; mode: string; settings_json?: any }[]>("/admin/providers");
}

export async function updateProviderSetting(
  key: string,
  payload: { enabled?: boolean; priority?: number; mode?: string; settings_json?: any }
) {
  const res = await authFetch(`/admin/providers/${encodeURIComponent(key)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Update failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function seedProviderDefaults() {
  const res = await authFetch("/admin/providers/seed-defaults", { method: "POST" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Seed failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function getWebCrawlProviderConfig(): Promise<WebCrawlProviderConfig> {
  return apiGet<WebCrawlProviderConfig>("/admin/providers/web-crawl");
}

export async function updateWebCrawlProviderConfig(
  payload: Partial<WebCrawlProviderConfig>
): Promise<WebCrawlProviderConfig> {
  const res = await authFetch("/admin/providers/web-crawl", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Update failed (${res.status}): ${txt}`);
  }
  return res.json();
}

async function apiPost(path: string, body: any) {
  const res = await authFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Request failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function requestBid(payload: {
  listing_id: number;
  max_bid?: number;
  destination_country: string;
  full_name: string;
  phone: string;
}) {
  const res = await authFetch("/broker/request-bid", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

// ============================================================================
// Data Engine API
// ============================================================================

export async function listDataSources(enabledOnly = false) {
  const qs = enabledOnly ? "?enabled_only=true" : "";
  return apiGet<any[]>(`/admin/data/sources${qs}`);
}

export async function getDataSource(sourceId: number) {
  return apiGet<any>(`/admin/data/sources/${sourceId}`);
}

export async function createDataSource(payload: any) {
  return apiPost("/admin/data/sources", payload);
}

export async function updateDataSource(sourceId: number, payload: any) {
  const res = await authFetch(`/admin/data/sources/${sourceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Update failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function deleteDataSource(sourceId: number) {
  const res = await authFetch(`/admin/data/sources/${sourceId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Delete failed (${res.status}): ${txt}`);
  }
}

export async function toggleDataSource(sourceId: number) {
  return apiPost(`/admin/data/sources/${sourceId}/toggle`, {});
}

export async function runDataSource(sourceId: number) {
  return apiPost(`/admin/data/sources/${sourceId}/run`, {});
}

export async function listSourceRuns(sourceId: number) {
  return apiGet<any[]>(`/admin/data/sources/${sourceId}/runs`);
}

export async function getDataRun(runId: number) {
  return apiGet<any>(`/admin/data/runs/${runId}`);
}

export async function listRunItems(runId: number) {
  return apiGet<any[]>(`/admin/data/runs/${runId}/items`);
}

export async function listStagedListings() {
  return apiGet<any[]>("/admin/data/staged");
}

export async function getStagedListing(listingId: number) {
  return apiGet<any>(`/admin/data/staged/${listingId}`);
}

export async function approveStagedListing(listingId: number) {
  return apiPost(`/admin/data/staged/${listingId}/approve`, {});
}

export async function rejectStagedListing(listingId: number) {
  return apiPost(`/admin/data/staged/${listingId}/reject`, {});
}

export async function bulkApproveStagedListings(listingIds: number[]) {
  return apiPost("/admin/data/staged/bulk-approve", { listing_ids: listingIds });
}

export async function bulkRejectStagedListings(listingIds: number[]) {
  return apiPost("/admin/data/staged/bulk-reject", { listing_ids: listingIds });
}

export async function testProxyConnection(payload: {
  proxy_url: string;
  proxy_username?: string | null;
  proxy_password?: string | null;
}) {
  return apiPost("/admin/data/test-proxy", payload);
}
