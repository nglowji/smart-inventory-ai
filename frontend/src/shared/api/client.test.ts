import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";
import { ApiError } from "./errors";
import { allPages } from "./pagination";
import { expireSession, getToken, SESSION_EXPIRED, setToken } from "./session";

class MemoryStorage {
  private items = new Map<string, string>();
  getItem(key: string) {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.items.set(key, value);
  }
  removeItem(key: string) {
    this.items.delete(key);
  }
}

describe("HTTP session and cancellation boundaries", () => {
  it("preserves the success notice when a password change ends the session", () => {
    setToken("old-session");
    let notice = "";
    window.addEventListener(SESSION_EXPIRED, (event) => {
      if (event instanceof CustomEvent && typeof event.detail === "string")
        notice = event.detail;
    });
    expireSession("old-session", "Password changed; sign in again.");
    expect(getToken()).toBeNull();
    expect(notice).toBe("Password changed; sign in again.");
  });
  const fetchMock = vi.fn<typeof fetch>();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("sessionStorage", new MemoryStorage());
    vi.stubGlobal("window", new EventTarget());
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("attaches the current token without mutating caller headers", async () => {
    setToken("current-token");
    fetchMock.mockResolvedValue(Response.json({ total: 0 }));
    const headers = new Headers({ "X-Test": "unchanged" });
    await expect(api("/products", { headers })).resolves.toEqual({ total: 0 });
    expect(headers.has("Authorization")).toBe(false);
    const sent = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(sent.get("Authorization")).toBe("Bearer current-token");
  });

  it("does not let a stale 401 invalidate a newer successful login", async () => {
    setToken("old-token");
    let finish: (response: Response) => void = () => {
      throw new Error("Request not started");
    };
    fetchMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const expired = vi.fn();
    window.addEventListener(SESSION_EXPIRED, expired);
    const request = api("/products");
    setToken("new-token");
    finish(Response.json({ error: { code: "UNAUTHORIZED" } }, { status: 401 }));
    await expect(request).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBe("new-token");
    expect(expired).not.toHaveBeenCalled();
  });

  it("expires the matching session on 401", async () => {
    setToken("expired-token");
    fetchMock.mockResolvedValue(
      Response.json({ error: { code: "UNAUTHORIZED" } }, { status: 401 }),
    );
    const expired = vi.fn();
    window.addEventListener(SESSION_EXPIRED, expired);
    await expect(api("/products")).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
    expect(expired).toHaveBeenCalledOnce();
  });

  it("does not mistake a failed login for an expired active session", async () => {
    setToken("active-token");
    fetchMock.mockResolvedValue(
      Response.json({ error: { code: "UNAUTHORIZED" } }, { status: 401 }),
    );
    await expect(api("/auth/login", { method: "POST" })).rejects.toMatchObject({
      status: 401,
    });
    expect(getToken()).toBe("active-token");
  });

  it("handles non-JSON upstream errors without leaking HTML", async () => {
    fetchMock.mockResolvedValue(
      new Response("<html>internal failure</html>", { status: 502 }),
    );
    await expect(api("/products")).rejects.toMatchObject({
      status: 502,
      code: "UNKNOWN",
      message: "Yêu cầu không thành công.",
    });
  });

  it("stops paginated requests when the consumer cancels", async () => {
    const controller = new AbortController();
    fetchMock.mockImplementation(async () => {
      controller.abort();
      return Response.json({ items: ["first"], total: 2, page: 1, page_size: 1 });
    });
    await expect(allPages("/categories", controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
