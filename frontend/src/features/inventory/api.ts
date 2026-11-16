import { api } from "../../shared/api/client";
import { PAGE_SIZE } from "../../shared/api/pagination";
import { query } from "../../shared/api/query";
import type { Movement, MovementType, Page, Range } from "../../shared/contracts";

export type MovementInput = {
  product_id: string;
  movement_type: MovementType;
  quantity: string;
  reason: string | null;
  reference_code: string | null;
  supplier_id: string | null;
};
export type MovementFilters = Range & {
  sku?: string;
  movement_type?: MovementType | "";
  page?: number;
  page_size?: number;
};
export const fetchMovements = (filters: MovementFilters, signal?: AbortSignal) =>
  api<Page<Movement>>(
    `/stock/movements?${query({ page: 1, page_size: PAGE_SIZE, ...filters })}`,
    { signal },
  );
export const createMovement = (payload: MovementInput, idempotencyKey: string) =>
  api<Movement>("/stock/movements", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "Idempotency-Key": idempotencyKey },
  });
