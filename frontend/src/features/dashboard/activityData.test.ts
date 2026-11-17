import { describe, expect, it } from "vitest";
import { activityData } from "./activityData";

describe("daily warehouse activity", () => {
  it("fills missing calendar days without mixing transaction counts and quantities", () => {
    const series = activityData({
      date_from: "2026-11-15",
      date_to: "2026-11-17",
      daily_activity: [
        { date: "2026-11-15", count: 3 },
        { date: "2026-11-17", count: 5 },
      ],
    });
    expect(series.values).toEqual([3, 0, 5]);
    expect(series.total).toBe(8);
    expect(series.activeDays).toBe(2);
  });
  it("keeps date labels stable across month and year boundaries", () => {
    const series = activityData({
      date_from: "2026-12-31",
      date_to: "2027-01-02",
      daily_activity: [],
    });
    expect(series.labels).toEqual(["31/12", "01/01", "02/01"]);
    expect(series.values).toEqual([0, 0, 0]);
  });
});
