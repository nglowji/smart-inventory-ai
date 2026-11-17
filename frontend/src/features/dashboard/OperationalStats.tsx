import { quantity } from "../../shared/lib/format";
import type { DashboardInsights } from "./types";

export default function OperationalStats({ data }: { data: DashboardInsights }) {
  const adjustments = data.movement_types
    .filter((item) => item.movement_type.startsWith("ADJUST"))
    .reduce((total, item) => total + item.count, 0);
  return (
    <section className="operational-stats" aria-label="Chỉ số vận hành bổ sung">
      {[
        {
          label: "SKU hết hàng",
          value: data.health.out_of_stock,
          note: "Đang hoạt động · tồn bằng 0",
        },
        {
          label: "SKU chưa có xuất trong kỳ",
          value: data.without_outbound_skus,
          note: "SKU hoạt động · chưa có OUT",
        },
        {
          label: "SKU ngừng hoạt động",
          value: data.archived_skus,
          note: "Hiện tại · vẫn giữ lịch sử",
        },
        {
          label: "Lượt điều chỉnh trong kỳ",
          value: adjustments,
          note: "ADJUST_IN + ADJUST_OUT",
        },
      ].map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{quantity(item.value)}</strong>
          <small>{item.note}</small>
        </div>
      ))}
    </section>
  );
}
