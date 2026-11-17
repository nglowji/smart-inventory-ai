import type { AuditEvent } from "../../shared/contracts";

export const auditLabels: Record<AuditEvent, string> = {
  AI_REQUESTED: "Gửi câu hỏi AI",
  AI_TOOL_CALLED: "AI tra cứu dữ liệu",
  AI_RESPONSE_FAILED: "AI xử lý thất bại",
  LOGIN_FAILED: "Đăng nhập thất bại",
  LOGIN_SUCCESS: "Đăng nhập thành công",
  USER_CREATED: "Tạo tài khoản",
  USER_UPDATED: "Đổi quyền / trạng thái",
  USER_PASSWORD_RESET: "Admin đặt lại mật khẩu",
  PASSWORD_CHANGED: "Đổi mật khẩu cá nhân",
  PRODUCT_ARCHIVED: "Ẩn sản phẩm",
  STOCK_ADJUSTED: "Điều chỉnh tồn kho",
};
export const detailLabels: Record<string, string> = {
  tool_name: "Công cụ tra cứu",
  success: "Thành công",
  latency_ms: "Thời gian (ms)",
  code: "Mã kết quả",
  reason: "Kết quả",
  role: "Vai trò",
  old_role: "Quyền cũ",
  new_role: "Quyền mới",
  old_active: "Hoạt động trước",
  new_active: "Hoạt động sau",
  sku: "SKU",
  product_id: "Mã sản phẩm",
  movement_type: "Loại",
  quantity: "Số lượng",
};
export function isAuditEvent(value: string): value is AuditEvent {
  return Object.hasOwn(auditLabels, value);
}
