const SESSION_KEY = "smartinventory.access-token";
export const SESSION_EXPIRED = "smartinventory:session-expired";

export function getToken(): string | null {
  return sessionStorage.getItem(SESSION_KEY);
}

export function setToken(token: string | null): void {
  if (token) sessionStorage.setItem(SESSION_KEY, token);
  else sessionStorage.removeItem(SESSION_KEY);
}

export function expireSession(
  requestToken: string | null,
  message = "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
): void {
  // An old request must not invalidate a newer successful login.
  if (requestToken && requestToken === getToken()) {
    setToken(null);
    window.dispatchEvent(new CustomEvent<string>(SESSION_EXPIRED, { detail: message }));
  }
}
