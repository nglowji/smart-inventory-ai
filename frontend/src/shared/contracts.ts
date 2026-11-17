export type Unit = "PCS" | "KG" | "LITER";
export type MovementType = "IN" | "OUT" | "ADJUST_IN" | "ADJUST_OUT";
export type Role = "ADMIN" | "STAFF" | "VIEWER";

export type User = {
  id: string;
  email: string;
  role: Role;
};

export type ManagedUser = User & { is_active: boolean; created_at: string };
export type AuditEvent =
  | "LOGIN_FAILED"
  | "LOGIN_SUCCESS"
  | "USER_CREATED"
  | "USER_UPDATED"
  | "USER_PASSWORD_RESET"
  | "PASSWORD_CHANGED"
  | "PRODUCT_ARCHIVED"
  | "STOCK_ADJUSTED";
export type AuditEntry = {
  id: string;
  actor_id: string | null;
  actor_email: string | null;
  event_type: AuditEvent;
  target_type: string;
  target_id: string | null;
  details: Record<string, string | boolean>;
  request_id: string | null;
  created_at: string;
};
export type Product = {
  id: string;
  sku: string;
  name: string;
  unit: Unit;
  min_stock: string;
  on_hand: string;
  unit_cost_vnd: string;
  lead_time_days: number;
  is_active: boolean;
  category_id: string | null;
  default_supplier_id: string | null;
};
export type Category = { id: string; name: string; is_active: boolean };
export type Supplier = Category & {
  phone: string | null;
  email: string | null;
};
export type Movement = {
  id: string;
  product_id: string;
  sku: string;
  name: string;
  unit: string;
  movement_type: MovementType;
  quantity: string;
  stock_before: string;
  stock_after: string;
  reason: string | null;
  reference_code: string | null;
  actor_email: string;
  occurred_at: string;
};
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Summary = {
  total_active_skus: number;
  low_stock_count: number;
  estimated_inventory_value_vnd: string;
  movement_count: number;
  stock_by_unit: Record<string, string>;
  date_from: string;
  date_to: string;
  as_of: string;
};
export type Flow = {
  items: { date: string; unit: string; inbound: string; outbound: string }[];
  totals: Record<string, { inbound: string; outbound: string }>;
  date_from: string;
  date_to: string;
};
export type Range = { date_from: string; date_to: string };
