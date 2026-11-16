import { ApiError, responseError } from "./errors";
import { expireSession, getToken } from "./session";

const REQUEST_TIMEOUT_MS = 15_000;

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  const requestToken = getToken();
  if (requestToken) headers.set("Authorization", `Bearer ${requestToken}`);
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, signal });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Không thể kết nối máy chủ. Kiểm tra backend và thử lại.",
    );
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") expireSession(requestToken);
    throw responseError(response.status, payload);
  }
  return payload as T;
}
