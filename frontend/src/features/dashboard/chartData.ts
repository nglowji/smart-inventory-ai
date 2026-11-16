import type { Flow } from "../../shared/contracts";

export function chartData(flow: Flow, unit: string) {
  const rows = flow.items.filter((row) => row.unit === unit);
  const dates: string[] = [];
  const cursor = new Date(`${flow.date_from}T00:00:00Z`);
  const end = new Date(`${flow.date_to}T00:00:00Z`);
  while (cursor <= end) {
    dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  const values = new Map(rows.map((row) => [row.date, row]));
  return {
    rows,
    labels: dates.map((date) => date.slice(5).split("-").reverse().join("/")),
    inbound: dates.map((date) => Number(values.get(date)?.inbound ?? 0)),
    outbound: dates.map((date) => Number(values.get(date)?.outbound ?? 0)),
  };
}
