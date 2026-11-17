import type { ChartConfiguration } from "chart.js";
import { useMemo } from "react";
import { quantity } from "../../shared/lib/format";
import { Empty } from "../../shared/ui/Feedback";
import { activityData } from "./activityData";
import ChartCanvas from "./charts/ChartCanvas";
import ChartDataTable from "./charts/ChartDataTable";
import { axisTicks, chartAnimation, chartPalette } from "./charts/theme";
import type { DashboardInsights } from "./types";

export default function ActivityPanel({ data }: { data: DashboardInsights }) {
  const series = useMemo(() => activityData(data), [data]);
  const config = useMemo<ChartConfiguration<"line">>(
    () => ({
      type: "line",
      data: {
        labels: series.labels,
        datasets: [
          {
            label: "Số giao dịch",
            data: series.values,
            borderColor: chartPalette.green,
            backgroundColor: chartPalette.area,
            borderWidth: 2,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: chartAnimation(),
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { display: false } },
        scales: {
          x: {
            border: { display: false },
            grid: { display: false },
            ticks: { ...axisTicks, maxTicksLimit: 7 },
          },
          y: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: chartPalette.grid },
            ticks: { ...axisTicks, precision: 0 },
          },
        },
      },
    }),
    [series],
  );
  return (
    <section className="panel activity-panel">
      <header className="panel-heading">
        <div>
          <h2>Nhịp hoạt động của kho</h2>
          <p>Số giao dịch mỗi ngày · giờ Việt Nam</p>
        </div>
        <span className="badge soft">Theo kỳ</span>
      </header>
      <div className="activity-summary">
        <div>
          <strong>{quantity(series.total)}</strong>
          <span>giao dịch</span>
        </div>
        <div>
          <strong>
            {quantity(series.activeDays)}
            <small> / {series.rows.length}</small>
          </strong>
          <span>ngày có hoạt động</span>
        </div>
      </div>
      {series.total ? (
        <ChartCanvas
          config={config}
          label="Biểu đồ đường số giao dịch kho theo từng ngày"
        />
      ) : (
        <Empty
          title="Chưa có hoạt động trong kỳ"
          description="Thử chọn khoảng ngày dài hơn để xem nhịp hoạt động."
        />
      )}
      <ChartDataTable
        title="Số giao dịch theo ngày"
        headers={["Ngày", "Số giao dịch"]}
        rows={series.rows.map((row) => ({
          key: row.date,
          cells: [row.date, quantity(row.count)],
        }))}
      />
      <p className="panel-footnote">
        Bao gồm IN, OUT, ADJUST_IN và ADJUST_OUT; đếm giao dịch, không cộng số lượng khác
        đơn vị.
      </p>
    </section>
  );
}
