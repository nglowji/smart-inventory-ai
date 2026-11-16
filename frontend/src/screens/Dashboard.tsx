import { useEffect, useState } from "react";
import { api, errorMessage, query } from "../api";
import { dateTime, money, quantity } from "../format";
import type {
  Flow,
  Movement,
  Page,
  Product,
  Range,
  Summary,
  User,
} from "../types";
import type { Action } from "../components/Dialog";
import { Empty, Failure, Loading, MovementsTable } from "../components/Common";
import FlowChart from "../components/FlowChart";
import Icon from "../components/Icon";

export default function Dashboard({
  range,
  version,
  user,
  action,
  navigate,
  refresh,
}: {
  range: Range;
  version: number;
  user: User;
  action: (action: Action) => void;
  navigate: (screen: string, low?: boolean) => void;
  refresh: () => void;
}) {
  const [data, setData] = useState<{
    summary: Summary;
    flow: Flow;
    low: Page<Product>;
    latest: Page<Movement>;
  } | null>(null);
  const [error, setError] = useState("");
  const [unit, setUnit] = useState("PCS");
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal };
    setData(null);
    setError("");
    const dates = query(range);
    void Promise.all([
      api<Summary>(`/dashboard/summary?${dates}`, options),
      api<Flow>(`/dashboard/flow?${dates}`, options),
      api<Page<Product>>("/stock/balances?low_stock=true&page_size=5", options),
      api<Page<Movement>>(`/stock/movements?page_size=5&${dates}`, options),
    ])
      .then(([summary, flow, low, latest]) =>
        setData({ summary, flow, low, latest }),
      )
      .catch((err) => {
        if (!controller.signal.aborted) setError(errorMessage(err));
      });
    return () => controller.abort();
  }, [range.date_from, range.date_to, version]);
  if (error) return <Failure message={error} retry={refresh} />;
  if (!data) return <Loading />;
  const { summary, flow, low, latest } = data;
  const hasFlow = flow.items.some(
    (item) =>
      item.unit === unit &&
      (Number(item.inbound) > 0 || Number(item.outbound) > 0),
  );

  return (
    <>
      <div className="data-context">
        <span>
          <span className="status-dot" />
          Dữ liệu PostgreSQL
        </span>
        <span>Cập nhật {dateTime(summary.as_of)} · Giờ Việt Nam</span>
      </div>
      <section className="metric-grid" aria-label="Tổng quan kho">
        <button className="kpi" onClick={() => navigate("Sản phẩm")}>
          <div className="kpi-label">
            SKU đang hoạt động
            <Icon name="box" />
          </div>
          <strong>{quantity(summary.total_active_skus)}</strong>
          <span>
            Xem danh sách sản phẩm <Icon name="arrow" size={14} />
          </span>
        </button>
        <button
          className={`kpi ${summary.low_stock_count ? "kpi-warning" : ""}`}
          onClick={() => navigate("Sản phẩm", true)}
        >
          <div className="kpi-label">
            Dưới ngưỡng tối thiểu
            <Icon name="alert" />
          </div>
          <strong>
            {quantity(summary.low_stock_count)}
            <small>SKU</small>
          </strong>
          <span>
            {summary.low_stock_count
              ? "Cần kiểm tra và bổ sung"
              : "Chưa có sản phẩm dưới ngưỡng"}
            <Icon name="arrow" size={14} />
          </span>
        </button>
        <div className="kpi">
          <div className="kpi-label">
            Giá trị tồn kho<span className="badge soft">Ước tính</span>
          </div>
          <strong className="kpi-money">
            {money(summary.estimated_inventory_value_vnd)}
          </strong>
          <span>Tồn hiện tại × đơn giá · toàn bộ sản phẩm</span>
        </div>
        <button className="kpi" onClick={() => navigate("Giao dịch kho")}>
          <div className="kpi-label">
            Giao dịch trong kỳ
            <Icon name="activity" />
          </div>
          <strong>{quantity(summary.movement_count)}</strong>
          <span>
            Bao gồm nhập, xuất và điều chỉnh <Icon name="arrow" size={14} />
          </span>
        </button>
      </section>

      <section className="stock-totals" aria-label="T?ng t?n theo ??n v?">
        <span>T?ng l??ng t?n <small>to?n b? s?n ph?m</small></span>
        {Object.entries(summary.stock_by_unit).map(([stockUnit, amount]) => <div key={stockUnit}><strong>{quantity(amount)}</strong><span>{stockUnit}</span></div>)}
      </section>
      <div className="dashboard-grid">
        <section className="panel flow-panel">
          <header className="panel-heading">
            <div>
              <h2>Biến động nhập / xuất</h2>
              <p>
                Theo ngày · {range.date_from.split("-").reverse().join("/")} —{" "}
                {range.date_to.split("-").reverse().join("/")}
              </p>
            </div>
            <label>
              <span className="sr-only">Đơn vị biểu đồ</span>
              <select value={unit} onChange={(e) => setUnit(e.target.value)}>
                <option>PCS</option>
                <option>KG</option>
                <option>LITER</option>
              </select>
            </label>
          </header>
          <div className="flow-totals">
            <div>
              <span className="chart-key inbound" />
              Nhập kho
              <strong>
                {quantity(flow.totals[unit]?.inbound ?? "0")}{" "}
                <small>{unit}</small>
              </strong>
            </div>
            <div>
              <span className="chart-key outbound" />
              Xuất kho
              <strong>
                {quantity(flow.totals[unit]?.outbound ?? "0")}{" "}
                <small>{unit}</small>
              </strong>
            </div>
          </div>
          {hasFlow ? (
            <FlowChart flow={flow} unit={unit} />
          ) : (
            <Empty
              title={`Chưa có nhập / xuất ${unit}`}
              description="Chọn đơn vị hoặc khoảng ngày khác. Giao dịch điều chỉnh không tính vào biểu đồ này."
            >
              {user.role !== "VIEWER" && (
                <button
                  className="button"
                  onClick={() => action({ kind: "movement" })}
                >
                  <Icon name="plus" size={16} />
                  Tạo giao dịch
                </button>
              )}
            </Empty>
          )}
          <p className="panel-footnote">
            Số lượng được tách theo đơn vị; không bao gồm giao dịch điều chỉnh.
          </p>
        </section>
        <section className="panel low-panel">
          <header className="panel-heading">
            <div>
              <h2>
                Cần bổ sung hàng{" "}
                <span className={`badge ${low.total ? "warning" : "soft"}`}>
                  {low.total}
                </span>
              </h2>
              <p>Tồn hiện tại thấp hơn mức tối thiểu</p>
            </div>
            <Icon name="alert" />
          </header>
          {low.items.length ? (
            <div className="low-list">
              {low.items.map((p) => (
                <div className="low-item" key={p.id}>
                  <div className="low-item-title">
                    <div>
                      <strong>{p.name}</strong>
                      <span>
                        {p.sku} · {p.unit}
                      </span>
                    </div>
                    <span className="low-amount">
                      {quantity(p.on_hand)}{" "}
                      <small>/ {quantity(p.min_stock)}</small>
                    </span>
                  </div>
                  <div
                    className="stock-track"
                    aria-label={`Tồn ${quantity(p.on_hand)} trên ngưỡng ${quantity(p.min_stock)} ${p.unit}`}
                  >
                    <span
                      style={{
                        width: `${Math.max(0, Math.min(100, (Number(p.on_hand) / Number(p.min_stock)) * 100))}%`,
                      }}
                    />
                  </div>
                  <div className="low-item-bottom">
                    <span>Dưới mức tối thiểu</span>
                    {user.role !== "VIEWER" ? (
                      <button
                        className="text-button"
                        onClick={() =>
                          action({ kind: "movement", product: p, type: "IN" })
                        }
                      >
                        Nhập hàng <Icon name="arrow" size={14} />
                      </button>
                    ) : (
                      <span className="badge soft">Chỉ đọc</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="Chưa có cảnh báo tồn"
              description="Sản phẩm được cảnh báo khi đang hoạt động, có ngưỡng lớn hơn 0 và tồn thấp hơn ngưỡng."
            />
          )}
          <button
            className="panel-link"
            onClick={() => navigate("Sản phẩm", true)}
          >
            Xem danh sách dưới ngưỡng
            <Icon name="arrow" size={16} />
          </button>
        </section>
      </div>

      <section className="panel recent-panel">
        <header className="panel-heading">
          <div>
            <h2>Giao dịch gần đây</h2>
            <p>Lịch sử thực tế trong khoảng ngày đã chọn</p>
          </div>
          <button
            className="text-button"
            onClick={() => navigate("Giao dịch kho")}
          >
            Xem lịch sử <Icon name="arrow" size={16} />
          </button>
        </header>
        {latest.items.length ? (
          <MovementsTable items={latest.items} />
        ) : (
          <Empty
            title="Kho chưa có giao dịch trong kỳ"
            description="Khi bạn nhập, xuất hoặc điều chỉnh, lịch sử sẽ tự động xuất hiện tại đây."
          />
        )}
      </section>
    </>
  );
}
