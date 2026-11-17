export const chartPalette = {
  green: "#185d49",
  sage: "#bac8bb",
  warning: "#d2b784",
  danger: "#a43d36",
  muted: "#657168",
  grid: "#edf0e9",
  area: "#185d4914",
};
export function chartAnimation() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? (false as const)
    : { duration: 200 };
}
export const axisTicks = {
  color: chartPalette.muted,
  font: { size: 10, family: "Be Vietnam Pro" },
};
export function compactMoney(value: number) {
  return new Intl.NumberFormat("vi-VN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}
export function shortLabel(value: string, max = 25) {
  const clean = value.replace(/^\[DEMO\]\s*/, "");
  return clean.length > max ? clean.slice(0, max - 1) + "…" : clean;
}
