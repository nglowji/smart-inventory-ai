import type { Action } from "../features/operations/types";
import type { User } from "../shared/contracts";

export const navigation = [
  {
    id: "dashboard",
    label: "Tổng quan",
    icon: "overview",
    description: "Tình hình kho hàng, cảnh báo và hoạt động trong một góc nhìn.",
  },
  {
    id: "products",
    label: "Sản phẩm",
    icon: "box",
    description: "Quản lý danh mục hàng hóa và tồn kho theo từng SKU.",
  },
  {
    id: "categories",
    label: "Danh mục",
    icon: "list",
    description: "Sắp xếp sản phẩm thành những nhóm dễ quản lý.",
  },
  {
    id: "suppliers",
    label: "Nhà cung cấp",
    icon: "truck",
    description: "Thông tin đối tác cung ứng hàng hóa cho kho.",
  },
  {
    id: "movements",
    label: "Giao dịch kho",
    icon: "activity",
    description: "Theo dõi từng lần nhập, xuất và điều chỉnh tồn kho.",
  },
] as const;
export type ScreenId = (typeof navigation)[number]["id"];
export type Navigate = (screen: ScreenId, low?: boolean) => void;
export const roleLabels = {
  ADMIN: "Quản trị viên",
  STAFF: "Nhân viên kho",
  VIEWER: "Chỉ xem",
} as const;
export const actionLabels = {
  product: "Thêm sản phẩm",
  category: "Thêm danh mục",
  supplier: "Thêm nhà cung cấp",
  movement: "Tạo giao dịch",
  archive: "Ngừng hoạt động",
} as const;

export function screenDetails(screen: ScreenId) {
  const details = navigation.find((item) => item.id === screen);
  if (!details) throw new Error(`Unknown screen: ${screen}`);
  return details;
}
export function primaryActionFor(screen: ScreenId, user: User): Action | null {
  if (user.role === "ADMIN") {
    if (screen === "categories") return { kind: "category" };
    if (screen === "suppliers") return { kind: "supplier" };
    if (screen === "products") return { kind: "product" };
  }
  if (user.role !== "VIEWER" && (screen === "dashboard" || screen === "movements"))
    return { kind: "movement" };
  return null;
}
