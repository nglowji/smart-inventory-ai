import type { DashboardInsights } from "./types";

export function activityData(
  data: Pick<DashboardInsights, "date_from" | "date_to" | "daily_activity">,
) {
  const values = new Map(data.daily_activity.map((item) => [item.date, item.count]));
  const rows: { date: string; count: number }[] = [];
  const cursor = new Date(`${data.date_from}T00:00:00Z`);
  const end = new Date(`${data.date_to}T00:00:00Z`);
  while (cursor <= end) {
    const date = cursor.toISOString().slice(0, 10);
    rows.push({ date, count: values.get(date) ?? 0 });
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return {
    rows,
    total: rows.reduce((total, row) => total + row.count, 0),
    activeDays: rows.filter((row) => row.count > 0).length,
    labels: rows.map((row) => row.date.slice(5).split("-").reverse().join("/")),
    values: rows.map((row) => row.count),
  };
}
