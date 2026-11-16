export const quantity = (value: string | number) => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 3 }).format(Number(value))
// Money/quantity arithmetic lives in PostgreSQL Decimal; JS is used only for visual formatting.
export const money = (value: string) => {
  const [whole, fraction = '00'] = value.split('.')
  const formatted = new Intl.NumberFormat('vi-VN').format(BigInt(whole))
  return `${formatted}${Number(fraction) ? ',' + fraction.padEnd(2, '0') : ''} ₫`
}
export const localDate = (value: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit' }).format(value)
export const dateTime = (value: string) => new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
export const movementNames: Record<string, string> = { IN: 'Nhập kho', OUT: 'Xuất kho', ADJUST_IN: 'Điều chỉnh tăng', ADJUST_OUT: 'Điều chỉnh giảm' }
export const belowMinimum = (p: { min_stock: string; on_hand: string; is_active: boolean }) => p.is_active && Number(p.min_stock) > 0 && Number(p.on_hand) < Number(p.min_stock)
