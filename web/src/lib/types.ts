export type Vehicle = {
  id: number;
  make: string;
  model: string;
  trim?: string | null;
  year: number;
};

export type Listing = {
  id: number;
  title: string;
  price?: number | null;
  currency?: string | null;
  location?: string | null;
  end_date?: string | null;
  condition?: string | null;
  transmission?: string | null;
  mileage?: number | null;
  risk_flags?: any[] | null;
  vehicle: Vehicle;
};

export type SearchResult = {
  listing_id: number;
  title: string;
  year: number;
  make: string;
  model: string;
  trim?: string | null;
  price?: number | null;
  currency?: string | null;
  location?: string | null;
  end_date?: string | null;
  risk_flags?: any[] | null;
  score?: number | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type SearchItem = {
  id: string;
  title: string;
  year?: number | null;
  make?: string | null;
  model?: string | null;
  trim?: string | null;
  price?: number | null;
  currency?: string | null;
  location?: string | null;
  url?: string | null;
  source?: string | null;
  risk_flags?: any[] | null;
  thumbnail_url?: string | null;
};

export type SearchSource = {
  name: string;
  enabled: boolean;
  total?: number | null;
  message?: string | null;
  error?: string | null;
};

export type QuotaInfo = {
  limit: number | null;
  used: number | null;
  remaining: number | null;
  reset_at?: string | null;
};

export type SearchResponse = {
  items: SearchItem[];
  total: number;
  page: number;
  page_size: number;
  sources: SearchSource[];
  quota?: QuotaInfo | null;
  status?: string;
  job_id?: number | null;
  message?: string | null;
};

export type SearchJobResult = {
  title: string;
  year?: number | null;
  make?: string | null;
  model?: string | null;
  price?: number | null;
  location?: string | null;
  source_domain: string;
  url: string;
  fetched_at: string;
};

export type SearchJobResponse = {
  job_id: number;
  status: string;
  result_count?: number | null;
  error?: string | null;
  results: SearchJobResult[];
};

export type WebCrawlProviderConfig = {
  enabled: boolean;
  priority: number;
  allowlist: string[];
  rate_per_minute: number;
  concurrency: number;
  max_sources: number;
  min_results: number;
};

export type Plan = {
  id: number;
  key: string;
  slug?: string;
  name: string;
  description?: string | null;
  price_monthly?: number | null;
  features?: string[] | null;
  quotas?: Record<string, any> | null;
  searches_per_day?: number | null;
  is_active?: boolean;
  is_featured?: boolean;
  sort_order?: number;
  stripe_price_id_monthly?: string | null;
  stripe_price_id_yearly?: string | null;
  assist_one_shot_per_day?: number | null;
  assist_watch_enabled?: boolean | null;
  assist_watch_max_cases?: number | null;
  assist_watch_runs_per_day?: number | null;
  assist_ai_budget_cents_per_day?: number | null;
  assist_reruns_per_day?: number | null;
  alerts_enabled?: boolean | null;
  alerts_max_active?: number | null;
  alerts_cadence_minutes?: number | null;
};

export type AssistCard = {
  id: number;
  title: string;
  status: string;
  mode: string;
  progress_percent: number;
  last_activity_at?: string | null;
  next_run_at?: string | null;
  is_active?: boolean;
};

export type AssistCase = {
  id: number;
  title?: string | null;
  status: string;
  mode: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AssistStep = {
  id: number;
  step_key: string;
  status: string;
  output_json?: any;
  error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type AssistArtifact = {
  id: number;
  type: string;
  content_text?: string | null;
  content_json?: any;
  created_at?: string | null;
};

export type SavedSearchAlert = {
  id: number;
  name?: string | null;
  query_json: Record<string, any>;
  is_active: boolean;
  cadence_minutes?: number | null;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AlertMatch = {
  id: number;
  listing_id: string;
  listing_url?: string | null;
  title?: string | null;
  price?: number | null;
  location?: string | null;
  is_new: boolean;
  matched_at?: string | null;
};

export type NotificationItem = {
  id: number;
  type: string;
  title: string;
  body?: string | null;
  link_url?: string | null;
  is_read: boolean;
  created_at?: string | null;
};

// ============================================================================
// Data Engine Types
// ============================================================================

export type MergeRules = {
  auto_merge_enabled: boolean;
  require_year_make_model: boolean;
  require_price_or_url: boolean;
  min_confidence_score?: number | null;
};

export type DataSource = {
  id: number;
  key: string;
  name: string;
  base_url: string;
  is_enabled: boolean;
  mode: "list_only" | "follow_details";
  schedule_minutes: number;
  max_items_per_run: number;
  max_pages_per_run: number;
  rate_per_minute: number;
  concurrency: number;
  timeout_seconds: number;
  retry_count: number;
  settings_json?: Record<string, any> | null;
  merge_rules?: MergeRules | null;
  failure_count: number;
  disabled_reason?: string | null;
  last_block_reason?: string | null;
  last_blocked_at?: string | null;
  cooldown_until?: string | null;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type DataRun = {
  id: number;
  source_id: number;
  status: "queued" | "running" | "succeeded" | "failed" | "paused" | "blocked" | "proxy_failed";
  started_at?: string | null;
  finished_at?: string | null;
  pages_planned: number;
  pages_done: number;
  items_found: number;
  items_staged: number;
  error_summary?: string | null;
  debug_json?: Record<string, any> | null;
  proxy_id?: number | null;
  proxy_exit_ip?: string | null;
  proxy_error?: string | null;
  created_at: string;
};

export type StagedListingAttribute = {
  id: number;
  staged_listing_id: number;
  key: string;
  value_text?: string | null;
  value_num?: number | null;
  value_bool?: boolean | null;
  unit?: string | null;
  created_at: string;
};

export type ProxyEndpoint = {
  id: number;
  name: string;
  host: string;
  port: number;
  username?: string | null;
  scheme: string;
  is_enabled: boolean;
  weight: number;
  max_concurrency: number;
  region?: string | null;
  last_check_at?: string | null;
  last_check_status?: string | null;
  last_exit_ip?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
};

export type StagedListing = {
  id: number;
  run_id: number;
  source_key: string;
  source_listing_id?: string | null;
  canonical_url: string;
  title?: string | null;
  year?: number | null;
  make?: string | null;
  model?: string | null;
  price_amount?: number | null;
  currency: string;
  confidence_score?: number | null;
  odometer_value?: number | null;
  location?: string | null;
  listed_at?: string | null;
  sale_datetime?: string | null;
  fetched_at: string;
  status: "active" | "ended" | "unknown";
  auto_approved: boolean;
  created_at: string;
  updated_at: string;
  attributes: StagedListingAttribute[];
};

// ============================================================================
// CSV Import Types
// ============================================================================

export type AdminImport = {
  id: number;
  filename: string;
  file_size: number;
  sha256: string;
  status: "UPLOADED" | "PARSING" | "READY" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED";
  total_rows?: number | null;
  processed_rows: number;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  error_log?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type ImportUploadResponse = {
  import_id: number;
  filename: string;
  file_size: number;
  sha256: string;
  total_rows: number;
  detected_headers: string[];
  sample_preview: Record<string, any>[];
  suggested_mapping: Record<string, string>;
  status: string;
};

export type ImportStartRequest = {
  column_map: Record<string, string>;
  source_key?: string | null;
  skip_duplicates?: boolean;
};

// ============================================================================
// Auction Sales / Sold Results Types
// ============================================================================

export type AuctionSale = {
  id: number;
  vin?: string | null;
  lot_id?: string | null;
  auction_source: string;  // copart/iaai/unknown
  sale_status: string;  // sold/on_approval/no_sale/unknown
  sold_price?: number | null;  // Price in cents
  currency: string;
  sold_at?: string | null;
  location?: string | null;
  odometer_miles?: number | null;
  damage?: string | null;
  condition?: string | null;
  attributes: Record<string, any>;
  source_url: string;
  created_at: string;
  updated_at: string;
};

export type AuctionTracking = {
  id: number;
  target_url: string;
  target_type: string;  // list_page / detail_page
  make?: string | null;
  model?: string | null;
  page_num?: number | null;
  status: string;  // pending/running/done/failed
  attempts: number;
  last_error?: string | null;
  last_http_status?: number | null;
  stats: Record<string, any>;
  next_check_at?: string | null;
  created_at: string;
  updated_at: string;
};
