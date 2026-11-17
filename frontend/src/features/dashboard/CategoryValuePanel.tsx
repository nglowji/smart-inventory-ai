import type { ChartConfiguration } from "chart.js";
import { useMemo } from "react";
import { money, quantity } from "../../shared/lib/format";
import { Empty } from "../../shared/ui/Feedback";
import ChartCanvas from "./charts/ChartCanvas";
import ChartDataTable from "./charts/ChartDataTable";
import {
  axisTicks,
  chartAnimation,
  chartPalette,
  compactMoney,
  shortLabel,
} from "./charts/theme";
import type { DashboardInsights } from "./types";

export default function CategoryValuePanel({
  items,
  total,
}: {
  items: DashboardInsights["category_values"];
  total: string;
}) {
  const config = useMemo<ChartConfiguration<"bar">>(
    () => ({
      type: "bar",
      data: {
        labels: items.map((item) => shortLabel(item.name)),
        datasets: [
          {
            label: "Giá trị tồn ước tính (VND)",
            data: items.map((item) => Number(item.value_vnd)),
            backgroundColor: chartPalette.green,
            borderRadius: 4,
            maxBarThickness: 18,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        animation: chartAnimation(),
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (contexts) => items[contexts[0]?.dataIndex ?? 0]?.name ?? "",
              label: (context) => money(items[context.dataIndex]?.value_vnd ?? "0"),
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: chartPalette.grid },
            ticks: {
              ...axisTicks,
              maxTicksLimit: 4,
              callback: (value) => compactMoney(Number(value)),
            },
          },
          y: { border: { display: false }, grid: { display: false }, ticks: axisTicks },
        },
      },
    }),
    [items],
  );
  return (
    <section className="panel category-value-panel">
      <header className="panel-heading">
        <div>
          <h2>Giá trị tồn theo danh mục</h2>
          <p>6 danh mục lớn nhất và phần còn lại · toàn bộ SKU</p>
        </div>
        <span className="badge soft">Ước tính</span>
      </header>
      <div className="insight-total">
        <strong>{money(total)}</strong>
        <span>Tồn hiện tại × đơn giá hiện tại</span>
      </div>
      {items.some((item) => Number(item.value_vnd) > 0) ? (
        <ChartCanvas
          config={config}
          label="Biểu đồ thanh giá trị tồn kho theo danh mục, đơn vị VND"
        />
      ) : (
        <Empty
          title="Chưa có giá trị tồn"
          description="Biểu đồ xuất hiện khi sản phẩm có tồn và đơn giá lớn hơn 0."
        />
      )}
      {items.length > 0 && (
        <ChartDataTable
          title="Giá trị tồn theo danh mục"
          headers={["Danh mục", "Số SKU", "Giá trị ước tính"]}
          rows={items.map((item) => ({
            key: item.key,
            cells: [item.name, quantity(item.sku_count), money(item.value_vnd)],
          }))}
        />
      )}
      <p className="panel-footnote">
        Bao gồm hàng ngừng hoạt động còn tồn. Không phải doanh thu hoặc giá vốn kế toán.
      </p>
    </section>
  );
}
