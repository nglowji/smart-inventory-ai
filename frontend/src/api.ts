import type { Page } from './types'

const SESSION_KEY = 'smartinventory.access-token'
export const getToken = () => sessionStorage.getItem(SESSION_KEY)
export const setToken = (token: string | null) => token ? sessionStorage.setItem(SESSION_KEY, token) : sessionStorage.removeItem(SESSION_KEY)

const errorMessages: Record<string, string> = {
  VALIDATION_ERROR: 'Kiểm tra các trường bắt buộc, số lượng và định dạng dữ liệu.',
  SKU_ALREADY_EXISTS: 'Mã SKU đã tồn tại, kể cả sản phẩm đã ngừng hoạt động.',
  UNIT_IMMUTABLE: 'Sản phẩm đã có giao dịch. Bạn không thể thay đổi đơn vị.',
  INSUFFICIENT_STOCK: 'Không đủ tồn kho để xuất số lượng này.',
  PRODUCT_ARCHIVED: 'Sản phẩm đã ngừng hoạt động.',
  FORBIDDEN: 'Tài khoản của bạn không có quyền thực hiện thao tác này.',
  IDEMPOTENCY_CONFLICT: 'Mã giao dịch đã được dùng cho nội dung khác.',
  DATABASE_UNAVAILABLE: 'Không kết nối được cơ sở dữ liệu. Vui lòng thử lại.',
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) { super(message) }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, signal: options.signal ?? AbortSignal.timeout(15000) })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(0, 'NETWORK_ERROR', 'Không thể kết nối máy chủ. Kiểm tra backend và thử lại.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      setToken(null)
      window.dispatchEvent(new Event('session-expired'))
    }
    const detail = payload?.error
    throw new ApiError(response.status, detail?.code ?? 'UNKNOWN', errorMessages[detail?.code] ?? detail?.message ?? 'Yêu cầu không thành công.', detail?.request_id)
  }
  return payload as T
}

export function query(values: Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)) })
  return params.toString()
}

export async function allPages<T>(path: string): Promise<T[]> {
  const items: T[] = []
  let page = 1
  while (true) {
    const result = await api<Page<T>>(`${path}${path.includes('?') ? '&' : '?'}page=${page}&page_size=100`)
    items.push(...result.items)
    if (items.length >= result.total || !result.items.length) return items
    page += 1
  }
}

export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Đã xảy ra lỗi. Vui lòng thử lại.'
