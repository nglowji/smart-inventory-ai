import { describe, expect, it } from "vitest";
import { isValidRange, rangeFor } from "./dates";

describe("Vietnamese report periods", () => {
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
