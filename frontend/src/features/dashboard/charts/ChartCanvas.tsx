import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import type { ChartConfiguration } from "chart.js";
import { useEffect, useRef } from "react";

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);

export default function ChartCanvas<T extends "bar" | "line" | "doughnut">({
  config,
  label,
  className = "insight-chart",
}: {
  config: ChartConfiguration<T>;
  label: string;
  className?: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!canvas.current) return;
    const chart = new Chart<T>(canvas.current, config);
    return () => chart.destroy();
  }, [config]);
  return (
    <div className={className}>
      <canvas ref={canvas} role="img" aria-label={label} />
    </div>
  );
}
