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
};

export type Plan = {
  id: number;
  key: string;
  name: string;
  description?: string | null;
  price_monthly?: number | null;
  features?: Record<string, any> | null;
  quotas?: Record<string, any> | null;
  searches_per_day?: number | null;
  stripe_price_id_monthly?: string | null;
  stripe_price_id_yearly?: string | null;
  assist_one_shot_per_day?: number | null;
  assist_watch_enabled?: boolean | null;
  assist_watch_max_cases?: number | null;
  assist_watch_runs_per_day?: number | null;
  assist_ai_budget_cents_per_day?: number | null;
  assist_reruns_per_day?: number | null;
};

export type AssistCard = {
  id: number;
  title: string;
  status: string;
  mode: string;
  progress_percent: number;
  last_activity_at?: string | null;
  next_run_at?: string | null;
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
