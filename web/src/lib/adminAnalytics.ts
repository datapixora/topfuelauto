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
