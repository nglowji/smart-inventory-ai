import { api } from "../../shared/api/client";
import type { User } from "../../shared/contracts";

export type Credentials = { email: string; password: string };
export const fetchCurrentUser = (signal?: AbortSignal) =>
  api<User>("/auth/me", { signal });
export const requestLogin = (credentials: Credentials, signal?: AbortSignal) =>
  api<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
    signal,
  });
