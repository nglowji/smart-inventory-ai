import { quantity } from "../../shared/lib/format";
import type { DashboardInsights } from "./types";

const labels = {
  IN: "Nhập kho",
  OUT: "Xuất kho",
  ADJUST_IN: "Điều chỉnh tăng",
  ADJUST_OUT: "Điều chỉnh giảm",
};
export default function MovementMix({
  items,
}: {
  items: DashboardInsights["movement_types"];
}) {
  const total = items.reduce((sum, item) => sum + item.count, 0);
  return (
    <div className="movement-mix">
      <div className="movement-mix-heading">
        <h3>Cơ cấu giao dịch trong kỳ</h3>
        <span>{quantity(total)} lượt</span>
      </div>
      <div
        className="movement-mix-bar"
        role="img"
        aria-label={items
          .map((item) => `${labels[item.movement_type]}: ${item.count}`)
          .join(", ")}
      >
        {items
          .filter((item) => item.count > 0)
          .map((item) => (
            <span
              key={item.movement_type}
              className={`mix-${item.movement_type.toLowerCase()}`}
              style={{ width: `${(item.count / total) * 100}%` }}
            />
          ))}
      </div>
      <div className="movement-mix-legend">
        {items.map((item) => (
          <div key={item.movement_type}>
            <span className={`mix-key mix-${item.movement_type.toLowerCase()}`} />
            <span>{labels[item.movement_type]}</span>
            <strong>{quantity(item.count)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
