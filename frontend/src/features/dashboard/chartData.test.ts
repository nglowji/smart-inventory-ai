import { describe, expect, it } from "vitest";
import type { Flow } from "../../shared/contracts";
import { chartData } from "./chartData";

describe("chart display series", () => {
  it("fills missing dates while keeping quantities in their own unit", () => {
    const flow: Flow = {
      date_from: "2026-11-14",
      date_to: "2026-11-16",
      totals: {},
      items: [
        { date: "2026-11-14", unit: "PCS", inbound: "10.000", outbound: "2.000" },
        { date: "2026-11-16", unit: "LITER", inbound: "0.500", outbound: "0.100" },
      ],
    };
    expect(chartData(flow, "PCS")).toMatchObject({
      labels: ["14/11", "15/11", "16/11"],
      inbound: [10, 0, 0],
      outbound: [2, 0, 0],
    });
    expect(chartData(flow, "LITER").inbound).toEqual([0, 0, 0.5]);
  });
});
