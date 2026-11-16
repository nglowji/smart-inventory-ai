import { movementNames } from "./model";
import type { Movement } from "../../shared/contracts";
import { dateTime, quantity } from "../../shared/lib/format";
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
