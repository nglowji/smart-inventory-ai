import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { allPages, api, errorMessage } from '../api'
import { quantity } from '../format'
import type { Category, Product, Supplier, User } from '../types'
import Icon from './Icon'

export type Action =
  | { kind: 'product'; product?: Product }
  | { kind: 'archive'; product: Product }
  | { kind: 'movement'; product?: Product; type?: string }
  | { kind: 'category'; item?: Category }
  | { kind: 'supplier'; item?: Supplier }

export default function Dialog({ action, user, close, saved }: { action: Action; user: User; close: () => void; saved: (message: string) => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const retry = useRef<{ body: string; key: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [productId, setProductId] = useState(action.kind === 'movement' ? action.product?.id ?? '' : '')
  const [movementType, setMovementType] = useState(action.kind === 'movement' ? action.type ?? 'IN' : 'IN')
  const product = action.kind === 'product' || action.kind === 'archive' ? action.product : undefined
  const current = products.find(p => p.id === productId)
  const titles = { product: product ? 'Chỉnh sửa sản phẩm' : 'Thêm sản phẩm', archive: 'Ngừng hoạt động sản phẩm', movement: 'Tạo giao dịch kho', category: action.kind === 'category' && action.item ? 'Sửa danh mục' : 'Thêm danh mục', supplier: action.kind === 'supplier' && action.item ? 'Sửa nhà cung cấp' : 'Thêm nhà cung cấp' }

  useEffect(() => {
    ref.current?.showModal()
    return () => ref.current?.close()
  }, [])
  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        if (action.kind === 'product' || action.kind === 'movement') {
          const [cats, vendors, stock] = await Promise.all([
            allPages<Category>('/categories'), allPages<Supplier>('/suppliers'),
            action.kind === 'movement' ? allPages<Product>('/products?active=true') : Promise.resolve([]),
          ])
          if (active) { setCategories(cats); setSuppliers(vendors); setProducts(stock) }
        }
        if (active) setReady(true)
      } catch (err) { if (active) setError(errorMessage(err)) }
    }
    void load()
    return () => { active = false }
  }, [action.kind])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(''); setBusy(true)
    const data = new FormData(event.currentTarget)
    const value = (key: string) => String(data.get(key) ?? '').trim()
    try {
      if (action.kind === 'product') {
        const payload: Record<string, unknown> = {
          sku: value('sku'), name: value('name'), unit: value('unit'), min_stock: value('min_stock'),
          unit_cost_vnd: value('unit_cost_vnd'), lead_time_days: Number(value('lead_time_days')),
          category_id: value('category_id') || null, default_supplier_id: value('default_supplier_id') || null,
        }
        if (product) Object.keys(payload).forEach(key => { if (payload[key] === product[key as keyof Product]) delete payload[key] })
        await api(product ? `/products/${product.id}` : '/products', { method: product ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
      } else if (action.kind === 'archive') {
        await api(`/products/${action.product.id}/archive`, { method: 'POST' })
      } else if (action.kind === 'movement') {
        const body = JSON.stringify({ product_id: productId, movement_type: movementType, quantity: value('quantity'), reason: value('reason') || null, reference_code: value('reference_code') || null, supplier_id: movementType === 'IN' ? value('supplier_id') || null : null })
        if (retry.current?.body !== body) retry.current = { body, key: crypto.randomUUID() }
        await api('/stock/movements', { method: 'POST', body, headers: { 'Idempotency-Key': retry.current.key } })
      } else {
        const payload = action.kind === 'category' ? { name: value('name') } : { name: value('name'), phone: value('phone') || null, email: value('email') || null }
        const path = action.kind === 'category' ? '/categories' : '/suppliers'
        await api(action.item ? `${path}/${action.item.id}` : path, { method: action.item ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
      }
      saved(action.kind === 'movement' ? 'Đã ghi giao dịch. Tồn kho và dashboard được cập nhật.' : 'Đã lưu thay đổi thành công.')
    } catch (err) { setError(errorMessage(err)) }
    finally { setBusy(false) }
  }

  return <dialog className="modal" ref={ref} aria-labelledby="dialog-title" onCancel={event => { if (busy) event.preventDefault(); else close() }}>
    <header className="modal-header"><div><span className="eyebrow">KHO CHÍNH</span><h2 id="dialog-title">{titles[action.kind]}</h2></div><button className="icon-button" onClick={close} disabled={busy} aria-label="Đóng"><Icon name="close" /></button></header>
    <form onSubmit={submit}>
      <fieldset disabled={busy || !ready} className="form-fields">
        {action.kind === 'archive' ? <div className="archive-note"><p>Bạn muốn ngừng hoạt động <strong>{action.product.sku} — {action.product.name}</strong>?</p><p>Sản phẩm sẽ không thể nhập/xuất thêm. Tồn hiện tại và lịch sử vẫn được giữ lại.</p></div> : action.kind === 'product' ? <>
          <div className="form-row"><label>Mã SKU<input name="sku" defaultValue={product?.sku} required maxLength={64} autoFocus autoComplete="off" placeholder="VD: SP001" /></label><label>Đơn vị<select name="unit" defaultValue={product?.unit ?? 'PCS'}><option value="PCS">Cái (PCS)</option><option value="KG">Kilogram (KG)</option><option value="LITER">Lít (LITER)</option></select></label></div>
          <label>Tên sản phẩm<input name="name" defaultValue={product?.name} required maxLength={255} placeholder="Nhập tên sản phẩm" /></label>
          <div className="form-row"><label>Danh mục<select name="category_id" defaultValue={product?.category_id ?? ''}><option value="">Chưa phân loại</option>{categories.filter(c => c.is_active || c.id === product?.category_id).map(c => <option key={c.id} value={c.id}>{c.name}{!c.is_active ? ' (ngừng hoạt động)' : ''}</option>)}</select></label><label>Nhà cung cấp mặc định<select name="default_supplier_id" defaultValue={product?.default_supplier_id ?? ''}><option value="">Chưa chọn</option>{suppliers.filter(s => s.is_active || s.id === product?.default_supplier_id).map(s => <option key={s.id} value={s.id}>{s.name}{!s.is_active ? ' (ngừng hoạt động)' : ''}</option>)}</select></label></div>
          <div className="form-row"><label>Tồn tối thiểu<input name="min_stock" type="number" min="0" step="0.001" defaultValue={product?.min_stock ?? '0'} required /></label><label>Thời gian chờ nhập (ngày)<input name="lead_time_days" type="number" min="0" step="1" defaultValue={product?.lead_time_days ?? 7} required /></label></div>
          <label>Đơn giá ước tính (VND)<input name="unit_cost_vnd" type="number" min="0" step="0.01" defaultValue={product?.unit_cost_vnd ?? '0'} required /></label>
          <p className="form-help">Sản phẩm mới có tồn bằng 0. Thay đổi số lượng qua giao dịch nhập/xuất; không sửa tồn trực tiếp.</p>
        </> : action.kind === 'movement' ? <>
          <label>Sản phẩm<select required value={productId} onChange={event => setProductId(event.target.value)}><option value="">Chọn sản phẩm</option>{products.map(p => <option value={p.id} key={p.id}>{p.sku} — {p.name}</option>)}</select></label>
          {current && <div className="balance-preview"><span>Tồn hiện tại</span><strong>{quantity(current.on_hand)} {current.unit}</strong></div>}
          <div className="form-row"><label>Loại giao dịch<select value={movementType} onChange={event => setMovementType(event.target.value)}><option value="IN">Nhập kho</option><option value="OUT">Xuất kho</option>{user.role === 'ADMIN' && <><option value="ADJUST_IN">Điều chỉnh tăng</option><option value="ADJUST_OUT">Điều chỉnh giảm</option></>}</select></label><label>Số lượng {current ? `(${current.unit})` : ''}<input name="quantity" type="number" required min={current?.unit === 'PCS' ? '1' : '0.001'} step={current?.unit === 'PCS' ? '1' : '0.001'} placeholder="0" /></label></div>
          {movementType === 'IN' && <label>Nhà cung cấp<select name="supplier_id" defaultValue=""><option value="">Không chọn</option>{suppliers.filter(s => s.is_active).map(s => <option value={s.id} key={s.id}>{s.name}</option>)}</select></label>}
          <label>Lý do {movementType !== 'IN' ? '(bắt buộc)' : '(tùy chọn)'}<textarea name="reason" required={movementType !== 'IN'} minLength={movementType.startsWith('ADJUST') ? 10 : undefined} maxLength={2000} rows={3} placeholder={movementType.startsWith('ADJUST') ? 'Mô tả chênh lệch kiểm kê, tối thiểu 10 ký tự' : 'Ghi chú cho giao dịch này'} /></label>
          <label>Mã tham chiếu<input name="reference_code" maxLength={50} placeholder="VD: NK-001 (không bắt buộc)" /></label>
          <p className="form-help">Giao dịch đã ghi không thể sửa hoặc xóa. Hệ thống kiểm tra tồn và chống ghi trùng khi gửi lại.</p>
        </> : <>
          <label>Tên {action.kind === 'category' ? 'danh mục' : 'nhà cung cấp'}<input name="name" defaultValue={action.item?.name} required maxLength={action.kind === 'category' ? 120 : 200} autoFocus /></label>
          {action.kind === 'supplier' && <><label>Số điện thoại<input name="phone" defaultValue={action.item?.phone ?? ''} type="tel" maxLength={30} /></label><label>Email<input name="email" type="email" defaultValue={action.item?.email ?? ''} maxLength={255} /></label></>}
        </>}
      </fieldset>
      {!ready && !error && <p role="status" className="muted">Đang tải thông tin…</p>}
      {error && <p className="error-banner" role="alert">{error}</p>}
      <footer className="modal-footer"><button className="button" type="button" onClick={close} disabled={busy}>Hủy</button><button className={`button ${action.kind === 'archive' ? 'danger' : 'primary'}`} disabled={busy || !ready}>{busy ? 'Đang lưu…' : action.kind === 'archive' ? 'Ngừng hoạt động' : action.kind === 'movement' ? 'Ghi giao dịch' : 'Lưu thay đổi'}</button></footer>
    </form>
  </dialog>
}
