const messages: Record<string, string> = {
  LAST_ADMIN: "Phải giữ ít nhất một Admin đang hoạt động.",
  EMAIL_ALREADY_EXISTS: "Email đã được sử dụng.",
  CURRENT_PASSWORD_INVALID: "Mật khẩu hiện tại không đúng.",
  VALIDATION_ERROR: "Kiểm tra các trường bắt buộc, số lượng và định dạng dữ liệu.",
  SKU_ALREADY_EXISTS: "Mã SKU đã tồn tại, kể cả sản phẩm đã ngừng hoạt động.",
  UNIT_IMMUTABLE: "Sản phẩm đã có giao dịch. Bạn không thể thay đổi đơn vị.",
  INSUFFICIENT_STOCK: "Không đủ tồn kho để xuất số lượng này.",
  PRODUCT_ARCHIVED: "Sản phẩm đã ngừng hoạt động.",
  FORBIDDEN: "Tài khoản của bạn không có quyền thực hiện thao tác này.",
  IDEMPOTENCY_CONFLICT: "Mã giao dịch đã được dùng cho nội dung khác.",
  DATABASE_UNAVAILABLE: "Không kết nối được cơ sở dữ liệu. Vui lòng thử lại.",
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function responseError(status: number, payload: unknown): ApiError {
  const detail = isRecord(payload) && isRecord(payload.error) ? payload.error : {};
  const code = typeof detail.code === "string" ? detail.code : "UNKNOWN";
  const message =
    messages[code] ??
    (typeof detail.message === "string" ? detail.message : "Yêu cầu không thành công.");
  const requestId = typeof detail.request_id === "string" ? detail.request_id : undefined;
  return new ApiError(status, code, message, requestId);
}

export const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : "Đã xảy ra lỗi. Vui lòng thử lại.";
