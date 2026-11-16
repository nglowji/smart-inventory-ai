import { chartData } from "./chartData";
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { useEffect, useMemo, useRef } from "react";
import type { Flow } from "../../shared/contracts";
import { quantity } from "../../shared/lib/format";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

export default function FlowChart({ flow, unit }: { flow: Flow; unit: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const series = useMemo(() => chartData(flow, unit), [flow, unit]);
  useEffect(() => {
    if (!canvas.current) return;
    const chart = new Chart(canvas.current, {
      type: "bar",
      data: {
        labels: series.labels,
        datasets: [
          {
            label: `Nhập (${unit})`,
            data: series.inbound,
            backgroundColor: "#185d49",
            borderRadius: 3,
            maxBarThickness: 19,
          },
          {
            label: `Xuất (${unit})`,
            data: series.outbound,
            backgroundColor: "#bac8bb",
            borderRadius: 3,
            maxBarThickness: 19,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 200 },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${quantity(item.parsed.y ?? 0)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              maxTicksLimit: 8,
              color: "#6b746e",
              font: { size: 11, family: "Be Vietnam Pro" },
            },
          },
          y: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: "#edf0e9" },
            ticks: {
              color: "#6b746e",
              precision: unit === "PCS" ? 0 : 3,
              font: { size: 11 },
            },
          },
        },
      },
    });
    return () => chart.destroy();
  }, [series, unit]);
  return (
    <>
      <div className="chart-canvas">
        <canvas
          ref={canvas}
          role="img"
          aria-label={`Biểu đồ nhập và xuất ${unit}, từ ${flow.date_from} đến ${flow.date_to}`}
        />
      </div>
      <details className="chart-data">
        <summary>Xem dữ liệu biểu đồ</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Ngày</th>
                <th>Nhập ({unit})</th>
                <th>Xuất ({unit})</th>
              </tr>
            </thead>
            <tbody>
              {series.rows.map((row) => (
                <tr key={row.date}>
                  <td>{row.date}</td>
                  <td>{quantity(row.inbound)}</td>
                  <td>{quantity(row.outbound)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
