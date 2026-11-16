import { api } from "../../shared/api/client";
import { query } from "../../shared/api/query";
import type { Flow, Page, Product, Range, Summary } from "../../shared/contracts";
import { fetchMovements } from "../inventory/api";

export async function fetchDashboard(range: Range, signal: AbortSignal) {
  const dates = query(range);
  const [summary, flow, low, latest] = await Promise.all([
    api<Summary>(`/dashboard/summary?${dates}`, { signal }),
    api<Flow>(`/dashboard/flow?${dates}`, { signal }),
    api<Page<Product>>("/stock/balances?low_stock=true&page_size=5", { signal }),
    fetchMovements({ ...range, page_size: 5 }, signal),
  ]);
  return { summary, flow, low, latest };
}
