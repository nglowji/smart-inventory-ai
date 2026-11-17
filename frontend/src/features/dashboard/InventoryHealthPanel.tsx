import type { ChartConfiguration } from "chart.js";
import { useMemo } from "react";
import { quantity } from "../../shared/lib/format";
import { Empty } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import ChartCanvas from "./charts/ChartCanvas";
import { chartAnimation, chartPalette } from "./charts/theme";
import type { DashboardInsights } from "./types";

export default function InventoryHealthPanel({
  health,
  viewProducts,
}: {
  health: DashboardInsights["health"];
  viewProducts: (low?: boolean) => void;
}) {
  const total = health.healthy + health.low + health.out_of_stock;
  const rows = useMemo(
    () => [
      { label: "Đủ ngưỡng", value: health.healthy, color: chartPalette.green },
      { label: "Tồn thấp, còn hàng", value: health.low, color: chartPalette.warning },
      { label: "Hết hàng", value: health.out_of_stock, color: chartPalette.danger },
    ],
    [health],
  );
  const config = useMemo<ChartConfiguration<"doughnut">>(
    () => ({
      type: "doughnut",
      data: {
        labels: rows.map((row) => row.label),
        datasets: [
          {
            data: rows.map((row) => row.value),
            backgroundColor: rows.map((row) => row.color),
            borderWidth: 4,
            borderColor: "#ffffff",
            hoverOffset: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: chartAnimation(),
        cutout: "77%",
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) =>
                `${context.label}: ${quantity(Number(context.raw))} SKU`,
            },
          },
        },
      },
    }),
    [rows],
  );
  return (
    <section className="panel health-panel">
      <header className="panel-heading">
        <div>
          <h2>Sức khỏe tồn kho</h2>
          <p>SKU đang hoạt động · tại thời điểm hiện tại</p>
        </div>
        <span className="badge soft">Hiện tại</span>
      </header>
      {total ? (
        <>
          <div className="health-ring">
            <ChartCanvas
              config={config}
              label="Tỷ trọng SKU đủ ngưỡng, tồn thấp và hết hàng"
              className="health-chart"
            />
            <div className="health-ring-label">
              <strong>{quantity(total)}</strong>
              <span>SKU hoạt động</span>
            </div>
          </div>
          <div className="health-legend">
            {rows.map((row) => (
              <div key={row.label}>
                <span className="health-key" style={{ backgroundColor: row.color }} />
                <span>{row.label}</span>
                <strong>{quantity(row.value)}</strong>
                <small>
                  {((row.value / total) * 100).toLocaleString("vi-VN", {
                    maximumFractionDigits: 1,
                  })}
                  %
                </small>
              </div>
            ))}
          </div>
        </>
      ) : (
        <Empty
          title="Chưa có sản phẩm hoạt động"
          description="Thêm sản phẩm để theo dõi tình trạng tồn kho."
        />
      )}
      <button className="panel-link" onClick={() => viewProducts(true)}>
        Kiểm tra hàng cần bổ sung <Icon name="arrow" size={16} />
      </button>
    </section>
  );
}
