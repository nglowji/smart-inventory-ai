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
  {
    id: "assistant",
    label: "Trợ lý AI",
    icon: "chat",
    description: "Hỏi dữ liệu kho bằng tiếng Việt, có nguồn để đối chiếu.",
  },
  {
    id: "users",
    label: "Tài khoản",
    icon: "users",
    description: "Quản lý người dùng, vai trò và trạng thái truy cập.",
  },
  {
    id: "audit",
    label: "Nhật ký",
    icon: "audit",
    description: "Truy vết thao tác quan trọng theo người dùng và thời gian.",
  },
] as const;
export type ScreenId = (typeof navigation)[number]["id"];
export type Navigate = (screen: ScreenId, low?: boolean) => void;
export const actionLabels = {
  product: "Thêm sản phẩm",
  category: "Thêm danh mục",
  supplier: "Thêm nhà cung cấp",
  movement: "Tạo giao dịch",
  archive: "Ngừng hoạt động",
  account: "Thêm tài khoản",
  password: "Đổi mật khẩu",
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
    if (screen === "users") return { kind: "account" };
  }
  if (user.role !== "VIEWER" && (screen === "dashboard" || screen === "movements"))
    return { kind: "movement" };
  return null;
}

export function canAccessScreen(screen: ScreenId, user: User): boolean {
  return (screen !== "users" && screen !== "audit") || user.role === "ADMIN";
}
