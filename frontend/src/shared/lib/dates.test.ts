import { describe, expect, it } from "vitest";
import { isValidRange, presetFor, rangeFor } from "./dates";

describe("Vietnamese report periods", () => {
  it("keeps the selected preset when the report toolbar remounts", () => {
    const now = new Date("2026-11-16T05:00:00Z");
    expect(presetFor(rangeFor(7, now), now)).toBe("7");
    expect(presetFor({ date_from: "2026-11-01", date_to: "2026-11-05" }, now)).toBe(
      "custom",
    );
  });
  it("uses the new Vietnam day at the UTC boundary", () => {
    expect(rangeFor(7, new Date("2026-11-15T17:00:00Z"))).toEqual({
      date_from: "2026-11-10",
      date_to: "2026-11-16",
    });
  });
  it("counts both selected endpoints within the 366-day limit", () => {
    expect(isValidRange({ date_from: "2026-01-01", date_to: "2027-01-01" })).toBe(true);
    expect(isValidRange({ date_from: "2026-01-01", date_to: "2027-01-02" })).toBe(false);
    expect(isValidRange({ date_from: "2026-11-17", date_to: "2026-11-16" })).toBe(false);
  });
});
