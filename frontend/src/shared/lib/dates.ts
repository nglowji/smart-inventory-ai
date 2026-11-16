import type { Range } from "../contracts";
import { localDate } from "./format";

const DAY_MS = 86_400_000;
export function rangeFor(days: number, now = new Date()): Range {
  const end = localDate(now);
  const start = new Date(`${end}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - days + 1);
  return { date_from: start.toISOString().slice(0, 10), date_to: end };
}
export function isValidRange(range: Range): boolean {
  const difference = (Date.parse(range.date_to) - Date.parse(range.date_from)) / DAY_MS;
  return Number.isFinite(difference) && difference >= 0 && difference <= 365;
}

export function presetFor(range: Range, now = new Date()): string {
  const days = [7, 30, 90].find((count) => {
    const preset = rangeFor(count, now);
    return preset.date_from === range.date_from && preset.date_to === range.date_to;
  });
  return days === undefined ? "custom" : String(days);
}
