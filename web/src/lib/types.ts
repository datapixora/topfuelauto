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
