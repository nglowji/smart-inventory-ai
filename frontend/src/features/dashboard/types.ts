import type { MovementType, Unit } from "../../shared/contracts";

export type DashboardInsights = {
  health: { healthy: number; low: number; out_of_stock: number };
  archived_skus: number;
  without_outbound_skus: number;
  estimated_inventory_value_vnd: string;
  category_values: { key: string; name: string; value_vnd: string; sku_count: number }[];
  movement_types: { movement_type: MovementType; count: number }[];
  daily_activity: { date: string; count: number }[];
  top_outbound: Record<
    Unit,
    { product_id: string; sku: string; name: string; unit: Unit; quantity: string }[]
  >;
  date_from: string;
  date_to: string;
  timezone: string;
  as_of: string;
  has_demo_data: boolean;
};
