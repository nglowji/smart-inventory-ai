import type { Product } from "../../shared/contracts";

export function belowMinimum(
  product: Pick<Product, "min_stock" | "on_hand" | "is_active">,
): boolean {
  return (
    product.is_active &&
    Number(product.min_stock) > 0 &&
    Number(product.on_hand) < Number(product.min_stock)
  );
}
