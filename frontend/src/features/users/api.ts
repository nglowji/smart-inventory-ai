import { api } from "../../shared/api/client";
import { PAGE_SIZE } from "../../shared/api/pagination";
import { query } from "../../shared/api/query";
import type { ManagedUser, Page, Role } from "../../shared/contracts";

export type UserCreateInput = { email: string; role: Role; password: string };
export type UserPatchInput = { role?: Role; is_active?: boolean; password?: string };
export const fetchUsers = (page: number, search: string, signal: AbortSignal) =>
  api<Page<ManagedUser>>(`/users?${query({ page, page_size: PAGE_SIZE, search })}`, {
    signal,
  });
export const createUser = (payload: UserCreateInput) =>
  api<ManagedUser>("/users", { method: "POST", body: JSON.stringify(payload) });
export const updateUser = (id: string, payload: UserPatchInput) =>
  api<ManagedUser>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
