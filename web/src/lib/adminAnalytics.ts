import { apiGet } from "./api";

export type SearchSeriesPoint = {
  bucket: string;
  searches: number;
  zero_results: number;
  errors: number;
};

export type TopQuery = {
  query: string;
  count: number;
  zero_count: number;
};

export type ZeroQuery = {
  query: string;
  count: number;
};

export type ProviderStats = {
  provider: string;
  count: number;
  error_count: number;
  cache_hits: number;
};

export type SearchAnalyticsResponse = {
  range: string;
  series: SearchSeriesPoint[];
  top_queries: TopQuery[];
  zero_queries: ZeroQuery[];
  providers: ProviderStats[];
};

export async function fetchSearchAnalytics(range: string): Promise<SearchAnalyticsResponse> {
  return apiGet<SearchAnalyticsResponse>(`/admin/metrics/searches?range=${encodeURIComponent(range)}`);
}

export type SearchOverview = {
  total_users?: number;
  searches_today?: number;
  zero_results?: number;
  avg_latency_ms?: number;
};

export async function fetchSearchOverview(): Promise<SearchOverview> {
  return apiGet<SearchOverview>("/admin/metrics/overview");
}

export type QuotaSeriesPoint = {
  date: string;
  quota_exceeded_events: number;
  users_hit_quota: number;
};

export type QuotaMetrics = {
  today: { quota_exceeded_events: number; users_hit_quota: number };
  last_7d: { quota_exceeded_events: number; users_hit_quota: number };
  series_7d: QuotaSeriesPoint[];
};

export async function fetchQuotaMetrics(): Promise<QuotaMetrics> {
  return apiGet<QuotaMetrics>("/admin/metrics/quota");
}

export type UpgradeCandidate = {
  user_id: number;
  email: string;
  plan: { id: number | null; name: string | null };
  quota_exceeded_count: number;
  total_searches: number;
  last_quota_hit_at: string | null;
  first_quota_hit_at?: string | null;
};

export type UpgradeCandidatesResponse = {
  range_days: number;
  limit: number;
  items: UpgradeCandidate[];
};

export async function fetchUpgradeCandidates(days = 7, limit = 50): Promise<UpgradeCandidatesResponse> {
  return apiGet<UpgradeCandidatesResponse>(
    `/admin/metrics/upgrade-candidates?days=${encodeURIComponent(days)}&limit=${encodeURIComponent(limit)}`
  );
}
