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