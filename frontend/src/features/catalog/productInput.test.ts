import { describe, expect, it } from "vitest";
import type { Product } from "../../shared/contracts";
import { productInput } from "./productInput";

const product: Product = {
  id: "product-1",
  sku: "SP001",
  name: "Bút bi",
  unit: "PCS",
  on_hand: "1.000",
  min_stock: "10.000",
  unit_cost_vnd: "9999999999999999.99",
  lead_time_days: 7,
  category_id: "inactive-category",
  default_supplier_id: null,
  is_active: true,
};
function form() {
  const data = new FormData();
  for (const key of [
    "sku",
    "name",
    "unit",
    "min_stock",
    "unit_cost_vnd",
    "lead_time_days",
    "category_id",
    "default_supplier_id",
  ] as const)
    data.set(key, String(product[key] ?? ""));
  return data;
}

describe("product mutation contract", () => {
  it("sends only changed fields, preserving unchanged inactive references", () => {
    const data = form();
    data.set("name", "Tên mới");
    expect(productInput(data, product)).toEqual({ name: "Tên mới" });
  });
  it("keeps high precision money as a decimal string", () => {
    expect(productInput(form()).unit_cost_vnd).toBe("9999999999999999.99");
  });
  it("distinguishes clearing a relationship from an omitted patch field", () => {
    const data = form();
    data.set("category_id", "");
    expect(productInput(data, product)).toEqual({ category_id: null });
  });
});
