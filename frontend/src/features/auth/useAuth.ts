import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../../shared/api/errors";
import { getToken, SESSION_EXPIRED, setToken } from "../../shared/api/session";
import type { User } from "../../shared/contracts";
import type { Credentials } from "./api";
import { fetchCurrentUser, requestLogin } from "./api";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [message, setMessage] = useState("");
  const generation = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const epoch = ++generation.current;
    if (getToken()) {
      void fetchCurrentUser(controller.signal)
        .then(
          (value) => {
            if (!controller.signal.aborted && generation.current === epoch)
              setUser(value);
          },
          (error) => {
            if (!controller.signal.aborted && generation.current === epoch) {
              setToken(null);
              setMessage(errorMessage(error));
            }
          },
        )
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    } else setLoading(false);
    const expired = (event: Event) => {
      generation.current += 1;
      setUser(null);
      setLoading(false);
      setMessage(
        event instanceof CustomEvent && typeof event.detail === "string"
          ? event.detail
          : "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
      );
    };
    window.addEventListener(SESSION_EXPIRED, expired);
    return () => {
      controller.abort();
      generation.current += 1;
      window.removeEventListener(SESSION_EXPIRED, expired);
    };
  }, []);

  const login = useCallback(async (credentials: Credentials) => {
    const epoch = ++generation.current;
    const result = await requestLogin(credentials);
    if (epoch !== generation.current) return;
    setToken(result.access_token);
    try {
      const value = await fetchCurrentUser();
      if (epoch === generation.current) {
        setUser(value);
        setMessage("");
      }
    } catch (error) {
      if (epoch === generation.current) setToken(null);
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    generation.current += 1;
    setToken(null);
    setUser(null);
    setMessage("");
  }, []);
  return { user, loading, message, login, logout };
}
