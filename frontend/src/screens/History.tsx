import { useEffect, useState } from 'react'
import { api, errorMessage, query } from '../api'
import type { Movement, Page, Range } from '../types'
import { dateTime, movementNames } from '../format'
import { Empty, Failure, Loading, MovementsTable, Pagination, downloadCsv } from '../components/Common'
import Icon from '../components/Icon'

export default function History({ range, version, refresh }: { range: Range; version: number; refresh: () => void }) {
  const [sku, setSku] = useState('')
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Page<Movement> | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { const timer = setTimeout(() => { setSearch(sku); setPage(1) }, 300); return () => clearTimeout(timer) }, [sku])
  useEffect(() => {
    const controller = new AbortController()
    setData(null); setError('')
    void api<Page<Movement>>(`/stock/movements?${query({ ...range, sku: search, movement_type: type, page, page_size: 10 })}`, { signal: controller.signal }).then(setData).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)) })
    return () => controller.abort()
  }, [search, type, page, range.date_from, range.date_to, version])
  return <section className="panel"><header className="panel-heading"><div><h2>Lịch sử giao dịch</h2><p>Bản ghi bất biến · Thời gian hiển thị theo giờ Việt Nam</p></div><button className="button" disabled={!data?.items.length} onClick={() => data && downloadCsv('giao-dich-trang-hien-tai.csv', ['Thời gian (VN)', 'SKU', 'Loại', 'Số lượng', 'Đơn vị', 'Tồn trước', 'Tồn sau', 'Người thực hiện', 'Lý do'], data.items.map(m => [dateTime(m.occurred_at), m.sku, movementNames[m.movement_type], m.quantity, m.unit, m.stock_before, m.stock_after, m.actor_email, m.reason ?? '']))}><Icon name="download" size={16} />Xuất trang CSV</button></header><div className="toolbar"><label className="search-field"><Icon name="search" size={18} /><input placeholder="Lọc theo mã SKU chính xác…" aria-label="Lọc giao dịch theo SKU" value={sku} onChange={e => setSku(e.target.value)} /></label><select aria-label="Loại giao dịch" value={type} onChange={e => { setType(e.target.value); setPage(1) }}><option value="">Tất cả giao dịch</option>{Object.entries(movementNames).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></div>{error ? <Failure message={error} retry={refresh} /> : !data ? <Loading /> : <>{data.items.length ? <MovementsTable items={data.items} /> : <Empty title="Chưa có giao dịch phù hợp" description="Thay đổi khoảng ngày hoặc bộ lọc để xem lịch sử khác." />}<Pagination page={page} total={data.total} change={setPage} /></>}</section>
}
