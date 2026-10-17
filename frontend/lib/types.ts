export type Category = "exhibition" | "play" | "musical";
export type PriceType = "free" | "paid" | "unknown";

export interface SourceRef {
  source: string;
  source_name: string;
  external_url?: string;
  attribution: string;
}

export interface CultureEvent {
  id: string;
  title: string;
  category: Category;
  venue_name: string;
  district?: string;
  start_date: string;
  end_date: string;
  price_type: PriceType;
  min_price?: number;
  max_price?: number;
  price_text?: string;
  description?: string;
  booking_url?: string;
  registered_at: string;
  updated_at: string;
  sources: SourceRef[];
}

export interface EventResponse {
  items: CultureEvent[];
  total: number;
  page: number;
  page_size: number;
  last_synced_at: string;
}

