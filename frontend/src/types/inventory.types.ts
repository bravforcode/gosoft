export type ProductStatus = "ok" | "low" | "critical" | "empty";

export interface Vendor {
  id: string;
  name: string;
  lead_time_days: number;
}

export interface ProductSummary {
  id: string;
  sku: string;
  name_th: string;
  name_en: string;
  brand: string;
  category: string;
  zone_id: string;
  camera_id: string;
  max_capacity: number;
  current_stock: number;
  reorder_threshold: number;
  reorder_quantity: number;
  unit_cost: number;
  unit_price: number;
  product_color_hex: string;
  shelf_position: Record<string, unknown>;
  image_url?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  vendor?: Vendor | null;
}

export interface StockHistoryPoint {
  timestamp: string;
  current_stock: number;
  fullness_after: number;
}

export interface ProductDetail extends ProductSummary {
  alerts: AlertSummary[];
  events: DetectionEvent[];
  stock_history: StockHistoryPoint[];
}

export interface DetectionEvent {
  id: string;
  camera_id: string;
  zone: string;
  event_type: string;
  severity: "info" | "warning" | "critical";
  confidence: number;
  fullness_after: number;
  created_at: string;
}

export interface AlertSummary {
  id: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
  status: "active" | "acknowledged" | "resolved" | "auto_resolved";
  created_at: string;
  evidence_frame_url?: string | null;
}

export interface PaginatedProducts {
  items: ProductSummary[];
  pagination: {
    total: number;
    skip: number;
    limit: number;
  };
}
