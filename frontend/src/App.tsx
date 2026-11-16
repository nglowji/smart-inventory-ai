import { useEffect, useRef, useState } from 'react'
import type { Product } from './demo'
import { formatMoney, formatQuantity, lowStock, products } from './demo'

type Screen = 'Tổng quan' | 'Sản phẩm' | 'Danh mục' | 'Nhà cung cấp' | 'Giao dịch kho' | 'Trợ lý AI'
const screens: Screen[] = ['Tổng quan', 'Sản phẩm', 'Danh mục', 'Nhà cung cấp', 'Giao dịch kho', 'Trợ lý AI']

function ProductDialog({ product, onClose }: { product: Product | 'new'; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    dialog.current?.showModal()
    return () => dialog.current?.close()
  }, [])
  const isNew = product === 'new'
  return (
    <dialog ref={dialog} className="product-dialog" onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose() }}>
      <div className="dialog-top"><span className="eyebrow">BẢN XEM TRƯỚC FORM</span><button onClick={onClose} className="icon-button" aria-label="Đóng hộp thoại">×</button></div>
      <h2>{isNew ? 'Thêm sản phẩm' : product.name}</h2>
      <p className="muted">Thông tin rõ ràng ngay từ sản phẩm đầu tiên.</p>
      <div className="form-preview">
        <label>Mã SKU<input defaultValue={isNew ? '' : product.sku} placeholder="Ví dụ: SP006" /></label>
        <label>Tên sản phẩm<input defaultValue={isNew ? '' : product.name} placeholder="Nhập tên sản phẩm" /></label>
        <div className="form-row"><label>Đơn vị<select defaultValue={isNew ? 'PCS' : product.unit}><option value="PCS">Cái (PCS)</option><option value="KG">Kilogram (KG)</option><option value="LITER">Lít (LITER)</option></select></label><label>Tồn tối thiểu<input inputMode="decimal" defaultValue={isNew ? '0' : product.minStock} /></label></div>
        <label>Đơn giá ước tính (VND)<input inputMode="decimal" defaultValue={isNew ? '0' : product.unitCost} /></label>
      </div>
      <div className="inline-note">Đây là bản xem trước bố cục. Thao tác lưu chưa kết nối API và không thay đổi dữ liệu kho.</div>
      <div className="dialog-actions"><button className="button" onClick={onClose}>Đóng</button><button className="button primary" disabled>Lưu sản phẩm</button></div>
    </dialog>
  )
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('Tổng quan')
  const [search, setSearch] = useState('')
  const [stockFilter, setStockFilter] = useState('all')
  const [mobileMenu, setMobileMenu] = useState(false)
  const [selected, setSelected] = useState<Product | 'new' | null>(null)
  const [tweaks, setTweaks] = useState(false)
  const [density, setDensity] = useState('balanced')
  const [dark, setDark] = useState(false)
  const lowProducts = products.filter(lowStock)
  const filtered = products.filter(product => {
    const query = search.trim().toLocaleLowerCase('vi')
    return `${product.sku} ${product.name}`.toLocaleLowerCase('vi').includes(query)
      && (stockFilter !== 'low' || lowStock(product))
  })
  const estimatedValue = products.reduce((sum, product) => sum + product.onHand * product.unitCost, 0)
  const catalogScreen = screen === 'Tổng quan' || screen === 'Sản phẩm'

  useEffect(() => { document.title = `SmartInventory — ${screen}` }, [screen])

  function navigate(next: Screen) {
    setScreen(next)
    setMobileMenu(false)
    setSearch('')
    setStockFilter('all')
  }

  return (
    <div className={`app ${dark ? 'dark' : ''} density-${density}`}>
      <a className="skip-link" href="#main-content">Đến nội dung chính</a>
      {mobileMenu && <button className="menu-backdrop" aria-label="Đóng menu" onClick={() => setMobileMenu(false)} />}
      <aside className={`sidebar ${mobileMenu ? 'is-open' : ''}`}>
        <a className="wordmark" href="#" onClick={event => { event.preventDefault(); navigate('Tổng quan') }}>Smart<span>Inventory</span><span className="wordmark-ai">AI</span></a>
        <div className="workspace"><div className="workspace-mark">K</div><div><strong>Kho chính</strong><span>Không gian làm việc</span></div><span className="workspace-chevron" aria-hidden="true">⌄</span></div>
        <p className="nav-label">QUẢN LÝ KHO</p>
        <nav aria-label="Điều hướng chính">{screens.map((item, index) => <button key={item} className={`nav-item ${screen === item ? 'active' : ''} ${index === 5 ? 'ai-nav' : ''}`} aria-current={screen === item ? 'page' : undefined} onClick={() => navigate(item)}><span>{item}</span>{item === 'Sản phẩm' && <span className="nav-count">5</span>}{item === 'Trợ lý AI' && <span className="read-only">Chỉ đọc</span>}</button>)}</nav>
        <div className="sidebar-bottom"><div className="quiet-rule" /><p>Một kho. Mọi thứ rõ ràng.</p><span>SmartInventory AI · Bản thiết kế v0</span><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Mở tài liệu API <span aria-hidden="true">↗</span></a></div>
      </aside>

      <div className="workspace-content">
        <header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Mở menu" aria-expanded={mobileMenu} onClick={() => setMobileMenu(!mobileMenu)}>☰</button><span>Không gian làm việc</span><span className="crumb-divider">/</span><strong>{screen}</strong></div><div className="topbar-right"><span className="prototype-label"><span className="status-dot" />Bản xem trước</span><span className="topbar-divider" /><div className="avatar" aria-label="Tài khoản minh họa Admin">AD</div></div></header>

        <main id="main-content" tabIndex={-1}>
          <div className="demo-notice"><span className="demo-label">DỮ LIỆU MẪU</span><p>Bản thiết kế giao diện — sử dụng bộ dữ liệu UAT, chưa kết nối kho thực.</p><span className="notice-version">v0</span></div>
          <div className="page-heading"><div><p className="page-kicker">KHO CHÍNH</p><h1>{screen === 'Tổng quan' ? 'Nắm rõ kho hàng của bạn.' : screen}</h1><p className="page-description">{screen === 'Tổng quan' ? 'Tồn kho, cảnh báo và sản phẩm — trong một góc nhìn.' : screen === 'Sản phẩm' ? 'Quản lý thông tin sản phẩm và theo dõi tồn kho theo từng SKU.' : 'Xem trước cấu trúc màn hình trong SmartInventory AI.'}</p></div>{catalogScreen && <button className="button primary" onClick={() => setSelected('new')}><span aria-hidden="true">＋</span>Thêm sản phẩm</button>}</div>

          {catalogScreen ? <>
            {screen === 'Tổng quan' && <section className="metrics" aria-label="Số liệu kho mẫu">
              <div className="metric"><div className="metric-label">Sản phẩm đang hoạt động<span className="metric-symbol" aria-hidden="true">↗</span></div><div className="metric-value">05<span>SKU</span></div><p>Trong bộ dữ liệu minh họa</p></div>
              <button className="metric metric-clickable" onClick={() => { setScreen('Sản phẩm'); setStockFilter('low') }}><div className="metric-label">Dưới mức tồn tối thiểu<span className="attention-symbol" aria-hidden="true">!</span></div><div className="metric-value warning-text">02<span>SKU</span></div><p><span className="warning-dot" />Cần kiểm tra để bổ sung hàng <span aria-hidden="true">→</span></p></button>
              <div className="metric"><div className="metric-label">Giá trị tồn kho<span className="estimate-badge">Ước tính</span></div><div className="metric-value money-value">1.367.000<span>₫</span></div><p>Tồn hiện tại × đơn giá sản phẩm</p><span className="sr-only">{formatMoney(estimatedValue)}</span></div>
            </section>}

            <div className={`content-grid ${screen === 'Sản phẩm' ? 'full-table' : ''}`}>
              <section className="panel product-panel" aria-labelledby="products-title">
                <div className="section-heading"><div><h2 id="products-title">{screen === 'Sản phẩm' ? 'Danh sách sản phẩm' : 'Sản phẩm trong kho'}<span className="count-badge">{products.length}</span></h2><p>Thông tin tồn kho theo từng đơn vị.</p></div>{screen === 'Tổng quan' && <button className="text-button" onClick={() => navigate('Sản phẩm')}>Xem tất cả <span aria-hidden="true">↗</span></button>}</div>
                <div className="table-toolbar"><label className="search-field"><span aria-hidden="true" className="search-mark" /><input aria-label="Tìm theo tên hoặc SKU" placeholder="Tìm theo tên hoặc SKU…" value={search} onChange={event => setSearch(event.target.value)} /><span className="search-hint">Tìm kiếm</span></label><label className="filter-field"><span className="sr-only">Lọc trạng thái tồn kho</span><select value={stockFilter} onChange={event => setStockFilter(event.target.value)}><option value="all">Tất cả trạng thái</option><option value="low">Dưới ngưỡng</option></select></label></div>
                <div className="table-scroll" role="region" aria-label="Bảng sản phẩm, có thể cuộn ngang" tabIndex={0}><table><thead><tr><th scope="col">Sản phẩm</th><th scope="col">Đơn vị</th><th scope="col" className="number">Tồn kho</th><th scope="col" className="number min-column">Tối thiểu</th><th scope="col">Trạng thái</th><th scope="col"><span className="sr-only">Chi tiết</span></th></tr></thead><tbody>{filtered.map(product => <tr key={product.sku}><td><button className="product-name" onClick={() => setSelected(product)}>{product.name}</button><span className="product-sku">{product.sku}</span></td><td><span className="unit-label">{product.unit}</span></td><td className={`number stock-number ${lowStock(product) ? 'warning-text' : ''}`}>{formatQuantity(product.onHand)}</td><td className="number muted min-column">{formatQuantity(product.minStock)}</td><td><span className={`stock-status ${lowStock(product) ? 'low' : product.minStock === 0 ? 'neutral' : 'healthy'}`}><span />{lowStock(product) ? 'Dưới ngưỡng' : product.minStock === 0 ? 'Không đặt ngưỡng' : 'Trong ngưỡng'}</span></td><td><button className="row-action" aria-label={`Xem ${product.name}`} onClick={() => setSelected(product)}>↗</button></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="empty-search"><h3>Không tìm thấy sản phẩm</h3><p>Thử một tên hoặc mã SKU khác.</p><button className="text-button" onClick={() => { setSearch(''); setStockFilter('all') }}>Xóa bộ lọc</button></div>}</div>
                <div className="table-footer"><span aria-live="polite">Hiển thị {filtered.length} / {products.length} sản phẩm mẫu</span><div className="pagination"><button disabled aria-label="Trang trước">‹</button><span aria-current="page">1</span><button disabled aria-label="Trang tiếp theo">›</button></div></div>
              </section>

              {screen === 'Tổng quan' && <aside className="right-column"><section className="panel attention-panel"><div className="section-heading compact"><h2>Cần chú ý<span className="count-badge warning-badge">2</span></h2></div><p className="section-description">Những sản phẩm đang dưới mức tồn tối thiểu.</p><div className="attention-list">{lowProducts.map(product => <button key={product.sku} className="attention-item" onClick={() => setSelected(product)}><div><strong>{product.name}</strong><span>{product.sku} · {product.unit}</span></div><div className="attention-quantity"><strong>{formatQuantity(product.onHand)}<small> / {formatQuantity(product.minStock)}</small></strong><span>Thiếu {formatQuantity(product.minStock - product.onHand)} {product.unit}</span></div></button>)}</div><p className="attention-footnote">Cảnh báo dựa trên ngưỡng bạn thiết lập.</p></section>
              <section className="ai-card"><div className="ai-card-top"><span className="ai-caption">TRỢ LÝ KHO HÀNG</span><span className="read-only">Chỉ đọc</span></div><h2>Hỏi một câu.<br />Hiểu rõ kho hàng.</h2><p>Tra cứu tồn và diễn giải số liệu bằng tiếng Việt.</p><button className="ai-prompt" onClick={() => navigate('Trợ lý AI')}>“Mặt hàng nào đang sắp hết?”<span aria-hidden="true">↗</span></button><span className="ai-coming">Bố cục dự kiến · chưa kết nối AI</span></section></aside>}
            </div>
            {screen === 'Tổng quan' && <section className="panel flow-placeholder"><div><span className="eyebrow">BIẾN ĐỘNG KHO</span><h2>Một góc nhìn xuyên suốt.</h2><p>Biểu đồ nhập / xuất theo ngày và đơn vị sẽ xuất hiện khi có dữ liệu giao dịch.</p></div><div className="chart-placeholder"><div className="chart-placeholder-lines" aria-hidden="true"><i /><i /><i /></div><span>Vùng biểu đồ · chờ triển khai</span></div></section>}
          </> : <section className="panel unfinished-screen"><span className="planned-label">MÀN HÌNH DỰ KIẾN</span><h2>{screen === 'Trợ lý AI' ? 'Dữ liệu thật. Câu trả lời có căn cứ.' : `${screen} — bước tiếp theo.`}</h2><p>{screen === 'Trợ lý AI' ? 'Trợ lý sẽ chỉ tra cứu và giải thích dữ liệu, không thực hiện nhập, xuất hay sửa kho.' : 'Bản v0 tập trung duyệt bố cục Tổng quan và Sản phẩm. Màn hình này chưa được kết nối.'}</p><button className="button" onClick={() => navigate('Tổng quan')}>Quay lại tổng quan <span aria-hidden="true">→</span></button></section>}

          <footer className="page-footer"><span>SmartInventory AI</span><span>Giao diện thử nghiệm · Số liệu không phải dữ liệu kho thực</span></footer>
        </main>
      </div>

      <div className="tweaks"><button className="tweaks-toggle" onClick={() => setTweaks(!tweaks)} aria-expanded={tweaks}>Tùy chỉnh giao diện <span aria-hidden="true">{tweaks ? '−' : '+'}</span></button>{tweaks && <section className="tweaks-panel" aria-label="Tùy chỉnh bản thiết kế"><strong>Tweaks</strong><label>Mật độ hiển thị<select value={density} onChange={event => setDensity(event.target.value)}><option value="comfortable">Thoáng</option><option value="balanced">Cân bằng</option><option value="compact">Gọn</option></select></label><label className="theme-switch"><input type="checkbox" checked={dark} onChange={event => setDark(event.target.checked)} />Giao diện tối</label><p>Chỉ thay đổi cách hiển thị bản mẫu.</p></section>}</div>
      {selected && <ProductDialog product={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
