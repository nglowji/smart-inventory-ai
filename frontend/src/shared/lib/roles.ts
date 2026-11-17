import type { Role } from "../contracts";

export const roleLabels: Record<Role, string> = {
  ADMIN: "Quản trị viên",
  STAFF: "Nhân viên kho",
  VIEWER: "Chỉ xem",
};
export function isRole(value: string): value is Role {
  return Object.hasOwn(roleLabels, value);
}
