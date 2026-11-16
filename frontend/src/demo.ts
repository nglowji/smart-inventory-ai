// Published UAT fixtures from the local master specification, never API/live inventory.
export type Product = {
  sku: string
  name: string
  unit: 'PCS' | 'KG' | 'LITER'
  minStock: number
  onHand: number
  unitCost: number
}

export const products: Product[] = [
  { sku: 'SP001', name: 'Bút bi xanh', unit: 'PCS', minStock: 10, onHand: 12, unitCost: 3500 },
  { sku: 'SP002', name: 'Vở A5', unit: 'PCS', minStock: 20, onHand: 15, unitCost: 12000 },
  { sku: 'SP003', name: 'Giấy A4', unit: 'PCS', minStock: 5, onHand: 8, unitCost: 65000 },
  { sku: 'SP004', name: 'Mực in đen', unit: 'LITER', minStock: 2, onHand: 1.5, unitCost: 350000 },
  { sku: 'SP005', name: 'Kẹp giấy', unit: 'PCS', minStock: 0, onHand: 100, unitCost: 1000 },
]

export const lowStock = (product: Product) => product.minStock > 0 && product.onHand < product.minStock
export const formatQuantity = (value: number) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 3 }).format(value)
export const formatMoney = (value: number) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
