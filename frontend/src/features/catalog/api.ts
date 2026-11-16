import { api } from "../../shared/api/client";
import { allPages, PAGE_SIZE } from "../../shared/api/pagination";
import { query } from "../../shared/api/query";
import type { Category, Page, Product, Supplier, Unit } from "../../shared/contracts";

export type ProductInput = {
  sku: string;
  name: string;
  unit: Unit;
  min_stock: string;
  unit_cost_vnd: string;
  lead_time_days: number;
  category_id: string | null;
  default_supplier_id: string | null;
};
export type ProductFilters = {
  search: string;
  page: number;
  active: string;
  low_stock: boolean;
  category_id: string;
};
export type MasterDataKind = "category" | "supplier";
const paths = { category: "/categories", supplier: "/suppliers" } as const;
export const fetchCategories = (signal?: AbortSignal) =>
  allPages<Category>(paths.category, signal);
export const fetchSuppliers = (signal?: AbortSignal) =>
  allPages<Supplier>(paths.supplier, signal);
export const fetchActiveProducts = (signal?: AbortSignal) =>
  allPages<Product>("/products?active=true", signal);
export const fetchProducts = (filters: ProductFilters, signal?: AbortSignal) =>
  api<Page<Product>>(`/stock/balances?${query({ ...filters, page_size: PAGE_SIZE })}`, {
    signal,
  });
export const saveProduct = (payload: Partial<ProductInput>, id?: string) =>
  api<Product>(id ? `/products/${id}` : "/products", {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });
export const archiveProduct = (id: string) =>
  api<Product>(`/products/${id}/archive`, { method: "POST" });
export const fetchMasterData = (
  kind: MasterDataKind,
  page: number,
  signal?: AbortSignal,
) =>
  api<Page<Category | Supplier>>(
    `${paths[kind]}?${query({ page, page_size: PAGE_SIZE })}`,
    { signal },
  );
export const setMasterDataActive = (kind: MasterDataKind, id: string, active: boolean) =>
  api<Category | Supplier>(`${paths[kind]}/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: active }),
  });
export const saveCategory = (name: string, id?: string) =>
  api<Category>(id ? `${paths.category}/${id}` : paths.category, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify({ name }),
  });
export const saveSupplier = (
  payload: { name: string; phone: string | null; email: string | null },
  id?: string,
) =>
  api<Supplier>(id ? `${paths.supplier}/${id}` : paths.supplier, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });
