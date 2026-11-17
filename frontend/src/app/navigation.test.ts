import { describe, expect, it } from "vitest";
import type { Role, User } from "../shared/contracts";
import { canAccessScreen, primaryActionFor } from "./navigation";

function user(role: Role): User {
  return { id: "user-1", email: "user@example.com", role };
}

describe("navigation permissions", () => {
  it.each(["STAFF", "VIEWER"] as const)(
    "hides account and audit management from %s",
    (role) => {
      expect(canAccessScreen("users", user(role))).toBe(false);
      expect(canAccessScreen("audit", user(role))).toBe(false);
      expect(primaryActionFor("users", user(role))).toBeNull();
      expect(canAccessScreen("dashboard", user(role))).toBe(true);
    },
  );
  it("allows only administrators to create accounts", () => {
    expect(canAccessScreen("users", user("ADMIN"))).toBe(true);
    expect(primaryActionFor("users", user("ADMIN"))).toEqual({ kind: "account" });
    expect(primaryActionFor("dashboard", user("VIEWER"))).toBeNull();
  });
});
