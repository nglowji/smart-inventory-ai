import { useEffect, useState } from 'react'
import { allPages, api, errorMessage, query } from '../api'
import type { Category, Page, Product, Supplier, User } from '../types'
import type { Action } from '../components/Dialog'
import { Empty, Failure, Loading, Pagination, downloadCsv } from '../components/Common'
import { belowMinimum, money, quantity } from '../format'
import Icon from '../components/Icon'

export function Products({ user, version, initialLow, action, refresh }: { user: User; version: number; initialLow: boolean; action: (action: Action) => void; refresh: () => void }) {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [active, setActive] = useState('true')
  const [low, setLow] = useState(initialLow)
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<Product> | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [error, setError] = useState('')
  useEffect(() => { const timer = setTimeout(() => { setDebounced(search); setPage(1) }, 300); return () => clearTimeout(timer) }, [search])
  useEffect(() => {
    const controller = new AbortController()
    setError(''); setData(null)
    void Promise.all([
      api<Page<Product>>(`/stock/balances?${query({ search: debounced, page, page_size: 10, active, low_stock: low, category_id: category })}`, { signal: controller.signal }),
      allPages<Category>('/categories'),
    ]).then(([result, cats]) => { if (!controller.signal.aborted) { setData(result); setCategories(cats) } }).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)) })
    return () => controller.abort()
  }, [debounced, page, active, low, category, version])

  return <section className="panel"><header className="panel-heading"><div><h2>Danh sách sản phẩm</h2><p>Mỗi SKU có một dòng tồn kho, không sửa số dư trực tiếp.</p></div><button className="button" disabled={!data?.items.length} onClick={() => data && downloadCsv('san-pham-trang-hien-tai.csv', ['SKU', 'Tên', 'Đơn vị', 'Tồn', 'Tối thiểu', 'Đơn giá (VND)'], data.items.map(p => [p.sku, p.name, p.unit, p.on_hand, p.min_stock, p.unit_cost_vnd]))}><Icon name="download" size={16} />Xuất trang CSV</button></header>
    <div className="toolbar"><label className="search-field"><Icon name="search" size={18} /><input placeholder="Tìm tên sản phẩm hoặc mã SKU…" aria-label="Tìm sản phẩm" value={search} onChange={e => setSearch(e.target.value)} /></label><select aria-label="Lọc danh mục" value={category} onChange={e => { setCategory(e.target.value); setPage(1) }}><option value="">Tất cả danh mục</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select><select aria-label="Trạng thái sản phẩm" value={active} onChange={e => { setActive(e.target.value); setLow(false); setPage(1) }}><option value="true">Đang hoạt động</option><option value="false">Ngừng hoạt động</option></select><label className="checkbox-label"><input type="checkbox" checked={low} disabled={active === 'false'} onChange={e => { setLow(e.target.checked); setPage(1) }} />Dưới ngưỡng</label></div>
    {error ? <Failure message={error} retry={refresh} /> : !data ? <Loading /> : <>{data.items.length ? <div className="table-scroll"><table><thead><tr><th>Sản phẩm / SKU</th><th>Danh mục</th><th className="number">Tồn kho</th><th className="number">Tối thiểu</th><th className="number">Đơn giá ước tính</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{data.items.map(p => <tr key={p.id}><td><strong>{p.name}</strong><span className="cell-sub">{p.sku}</span></td><td className="muted">{categories.find(c => c.id === p.category_id)?.name ?? 'Chưa phân loại'}</td><td className={`number ${belowMinimum(p) ? 'warning-text' : ''}`}><strong>{quantity(p.on_hand)}</strong><span className="cell-sub">{p.unit}</span></td><td className="number">{quantity(p.min_stock)}</td><td className="number nowrap">{money(p.unit_cost_vnd)}</td><td><span className={`badge ${!p.is_active ? 'soft' : belowMinimum(p) ? 'warning' : 'success'}`}>{!p.is_active ? 'Ngừng hoạt động' : belowMinimum(p) ? 'Dưới ngưỡng' : 'Trong ngưỡng'}</span></td><td><div className="row-actions">{user.role !== 'VIEWER' && p.is_active && <button className="small-button" onClick={() => action({ kind: 'movement', product: p })}>Nhập / xuất</button>}{user.role === 'ADMIN' && <><button className="small-button" onClick={() => action({ kind: 'product', product: p })}>Sửa</button>{p.is_active && <button className="small-button danger-text" onClick={() => action({ kind: 'archive', product: p })}>Ẩn</button>}</>}{user.role === 'VIEWER' && <span className="muted">Chỉ đọc</span>}</div></td></tr>)}</tbody></table></div> : <Empty title="Không có sản phẩm phù hợp" description="Thay đổi bộ lọc hoặc thêm sản phẩm đầu tiên để bắt đầu theo dõi kho.">{user.role === 'ADMIN' && <button className="button primary" onClick={() => action({ kind: 'product' })}><Icon name="plus" size={16} />Thêm sản phẩm</button>}</Empty>}<Pagination total={data.total} page={page} change={setPage} /></>}
  </section>
}

export function MasterData({ kind, user, version, action, refresh, notify }: { kind: 'category' | 'supplier'; user: User; version: number; action: (action: Action) => void; refresh: () => void; notify: (message: string) => void }) {
  const [data, setData] = useState<Page<Supplier> | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [pending, setPending] = useState<string | null>(null)
  const path = kind === 'category' ? '/categories' : '/suppliers'
  useEffect(() => {
    const controller = new AbortController()
    setData(null); setError('')
    void api<Page<Supplier>>(`${path}?page=${page}&page_size=10`, { signal: controller.signal }).then(setData).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)) })
    return () => controller.abort()
  }, [path, page, version])
  async function toggle(item: Supplier) {
    setPending(item.id); setError('')
    try { await api(`${path}/${item.id}`, { method: 'PATCH', body: JSON.stringify({ is_active: !item.is_active }) }); notify('Đã cập nhật trạng thái.'); refresh() }
    catch (err) { setError(errorMessage(err)) }
    finally { setPending(null) }
  }
  return <section className="panel"><header className="panel-heading"><div><h2>{kind === 'category' ? 'Danh mục sản phẩm' : 'Danh sách nhà cung cấp'}</h2><p>Dữ liệu dùng chung cho toàn bộ kho.</p></div></header>{error && <Failure message={error} retry={refresh} />}{!data && !error ? <Loading /> : data && <>{data.items.length ? <div className="table-scroll"><table><thead><tr><th>Tên</th>{kind === 'supplier' && <><th>Điện thoại</th><th>Email</th></>}<th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{data.items.map(item => <tr key={item.id}><td><strong>{item.name}</strong></td>{kind === 'supplier' && <><td>{item.phone ?? '—'}</td><td>{item.email ?? '—'}</td></>}<td><span className={`badge ${item.is_active ? 'success' : 'soft'}`}>{item.is_active ? 'Hoạt động' : 'Ngừng hoạt động'}</span></td><td>{user.role === 'ADMIN' ? <div className="row-actions"><button className="small-button" onClick={() => action(kind === 'category' ? { kind, item } : { kind, item })}>Chỉnh sửa</button><button disabled={pending === item.id} className="small-button" onClick={() => void toggle(item)}>{pending === item.id ? 'Đang lưu…' : item.is_active ? 'Ngừng hoạt động' : 'Kích hoạt'}</button></div> : <span className="muted">Chỉ đọc</span>}</td></tr>)}</tbody></table></div> : <Empty title={kind === 'category' ? 'Chưa có danh mục' : 'Chưa có nhà cung cấp'} description="Thêm dữ liệu để việc phân loại và nhập hàng dễ dàng hơn." />}<Pagination page={page} total={data.total} change={setPage} /></>}</section>
}
