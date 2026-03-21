export interface SIVEvent {
  id: string;
  type:
    | "stock_update"
    | "alert_created"
    | "alert_resolved"
    | "reorder_triggered"
    | "anomaly_detected"
    | "camera_status"
    | "po_approved"
    | "restock_confirmed"
    | "heartbeat";
  timestamp: string;
  camera_id?: string | null;
  zone?: string | null;
  product_id?: string | null;
  sku?: string | null;
  severity: "info" | "warning" | "critical";
  data: Record<string, unknown>;
  session_id: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "manager" | "operator" | "viewer";
  is_active: boolean;
  created_at: string;
}
