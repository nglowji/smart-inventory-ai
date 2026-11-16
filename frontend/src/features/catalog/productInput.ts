import type { Product, Unit } from "../../shared/contracts";
import { formText, optionalFormText } from "../../shared/lib/forms";
import type { ProductInput } from "./api";

const fields = [
  "sku",
  "name",
  "unit",
  "min_stock",
  "unit_cost_vnd",
  "lead_time_days",
  "category_id",
  "default_supplier_id",
] as const satisfies readonly (keyof ProductInput)[];
function parseUnit(value: string): Unit {
  if (value === "PCS" || value === "KG" || value === "LITER") return value;
  throw new Error("Đơn vị sản phẩm không hợp lệ.");
}
export function productInput(data: FormData, product?: Product): Partial<ProductInput> {
  const next: ProductInput = {
    sku: formText(data, "sku"),
    name: formText(data, "name"),
    unit: parseUnit(formText(data, "unit")),
    min_stock: formText(data, "min_stock"),
    unit_cost_vnd: formText(data, "unit_cost_vnd"),
    lead_time_days: Number(formText(data, "lead_time_days")),
    category_id: optionalFormText(data, "category_id"),
    default_supplier_id: optionalFormText(data, "default_supplier_id"),
  };
  if (!product) return next;
  const changed: Partial<ProductInput> = {};
  function include<K extends keyof ProductInput>(key: K) {
    if (next[key] !== product?.[key]) changed[key] = next[key];
  }
  fields.forEach(include);
  return changed;
}
