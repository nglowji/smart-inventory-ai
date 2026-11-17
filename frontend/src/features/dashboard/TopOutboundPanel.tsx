import type { ChartConfiguration } from "chart.js";
import { useMemo, useState } from "react";
import type { Unit } from "../../shared/contracts";
import { quantity } from "../../shared/lib/format";
import { Empty } from "../../shared/ui/Feedback";
import ChartCanvas from "./charts/ChartCanvas";
import ChartDataTable from "./charts/ChartDataTable";
import { axisTicks, chartAnimation, chartPalette } from "./charts/theme";
import type { DashboardInsights } from "./types";

export default function TopOutboundPanel({
  data,
}: {
  data: DashboardInsights["top_outbound"];
}) {
  const [unit, setUnit] = useState<Unit>("PCS");
  const items = data[unit];
  const config = useMemo<ChartConfiguration<"bar">>(
    () => ({
      type: "bar",
      data: {
        labels: items.map((item) => item.sku),
        datasets: [
          {
            label: `Lượng xuất (${unit})`,
            data: items.map((item) => Number(item.quantity)),
            backgroundColor: chartPalette.green,
            borderRadius: 4,
            maxBarThickness: 22,
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
              label: (context) =>
                `${quantity(items[context.dataIndex]?.quantity ?? "0")} ${unit}`,
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: chartPalette.grid },
            ticks: { ...axisTicks, precision: unit === "PCS" ? 0 : 3, maxTicksLimit: 5 },
          },
          y: { border: { display: false }, grid: { display: false }, ticks: axisTicks },
        },
      },
    }),
    [items, unit],
  );
  return (
    <section className="panel outbound-ranking-panel">
      <header className="panel-heading">
        <div>
          <h2>Sản phẩm xuất nhiều nhất</h2>
          <p>Top 5 theo lượng OUT trong kỳ</p>
        </div>
        <label>
          <span className="sr-only">Đơn vị xếp hạng xuất hàng</span>
          <select
            value={unit}
            onChange={(event) => {
              const value = event.target.value;
              if (value === "PCS" || value === "KG" || value === "LITER") setUnit(value);
            }}
          >
            <option>PCS</option>
            <option>KG</option>
            <option>LITER</option>
          </select>
        </label>
      </header>
      {items.length ? (
        <>
          <ChartCanvas
            config={config}
            label={`Top 5 SKU xuất nhiều nhất, đơn vị ${unit}`}
          />
          <ChartDataTable
            title={`Sản phẩm xuất nhiều nhất (${unit})`}
            headers={["SKU", "Sản phẩm", `Lượng xuất (${unit})`]}
            rows={items.map((item) => ({
              key: item.product_id,
              cells: [item.sku, item.name, quantity(item.quantity)],
            }))}
          />
        </>
      ) : (
        <Empty
          title={`Chưa có xuất hàng ${unit}`}
          description="Chọn đơn vị hoặc khoảng ngày khác để xem xếp hạng."
        />
      )}
      <p className="panel-footnote">
        Xếp hạng riêng từng đơn vị; không tính điều chỉnh giảm tồn.
      </p>
    </section>
  );
}
