import type { Movement } from "../types";
import { dateTime, movementNames, quantity } from "../format";
import Icon from "./Icon";

export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="box" size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" />
      Đang tải dữ liệu mới nhất…
    </div>
  );
}
export function Failure({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <Icon name="alert" />
      <h3>Chưa tải được dữ liệu</h3>
      <p>{message}</p>
      <button className="button" onClick={retry}>
        Thử lại
      </button>
    </div>
  );
}
export function Pagination({
  total,
  page,
  pageSize = 10,
  change,
}: {
  total: number;
  page: number;
  pageSize?: number;
  change: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="table-footer">
      <span>
        {total
          ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} / ${total} bản ghi`
          : "0 bản ghi"}
      </span>
      <div className="pagination">
        <button
          disabled={page <= 1}
          onClick={() => change(page - 1)}
          aria-label="Trang trước"
        >
          ‹
        </button>
        <span>
          Trang {page} / {pages}
        </span>
        <button
          disabled={page >= pages}
          onClick={() => change(page + 1)}
          aria-label="Trang sau"
        >
          ›
        </button>
      </div>
    </div>
  );
}
export function MovementsTable({ items }: { items: Movement[] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Thời gian</th>
            <th>Sản phẩm</th>
            <th>Loại giao dịch</th>
            <th className="number">Số lượng</th>
            <th className="number">Tồn trước → sau</th>
            <th>Người thực hiện / Lý do</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m) => (
            <tr key={m.id}>
              <td className="nowrap muted">{dateTime(m.occurred_at)}</td>
              <td>
                <strong>{m.name}</strong>
                <span className="cell-sub">
                  {m.sku}
                  {m.reference_code ? ` · ${m.reference_code}` : ""}
                </span>
              </td>
              <td>
                <span
                  className={`badge ${m.movement_type === "IN" ? "success" : m.movement_type === "OUT" ? "soft" : "warning"}`}
                >
                  {movementNames[m.movement_type]}
                </span>
              </td>
              <td className="number">
                <strong>{quantity(m.quantity)}</strong>
                <span className="cell-sub">{m.unit}</span>
              </td>
              <td className="number nowrap">
                {quantity(m.stock_before)} <span className="muted">→</span>{" "}
                {quantity(m.stock_after)}
              </td>
              <td>
                <span className="actor-email">{m.actor_email}</span>
                <span className="cell-sub reason-text">{m.reason ?? "—"}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function downloadCsv(
  filename: string,
  headers: string[],
  rows: string[][],
) {
  // Prefix formula-like strings so spreadsheet applications treat user-provided cells as text.
  const escape = (value: string) =>
    `"${(/^[=+@\-\t\r]/.test(value) ? "'" + value : value).replaceAll('"', '""')}"`;
  const content =
    "\uFEFF" +
    [headers, ...rows].map((row) => row.map(escape).join(",")).join("\r\n");
  const url = URL.createObjectURL(
    new Blob([content], { type: "text/csv;charset=utf-8;" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
