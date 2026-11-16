import type { FormEvent } from "react";
import { useState } from "react";
import { errorMessage } from "../../shared/api/errors";
import Icon from "../../shared/ui/Icon";
import type { Credentials } from "./api";

export default function LoginPage({
  login,
  message,
}: {
  login: (credentials: Credentials) => Promise<void>;
  message: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await login({
        email: String(data.get("email") ?? ""),
        password: String(data.get("password") ?? ""),
      });
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <a className="wordmark" href="/">
          Smart<span>Inventory</span>
          <span className="wordmark-ai">AI</span>
        </a>
        <div>
          <span className="eyebrow">KHÔNG GIAN VẬN HÀNH KHO</span>
          <h1>
            Mọi sản phẩm.
            <br />
            Mọi biến động.
            <br />
            <em>Trong tầm kiểm soát.</em>
          </h1>
          <p>
            Quản lý tồn kho chính xác, truy vết từng giao dịch và luôn biết khi nào cần bổ
            sung hàng.
          </p>
          <div className="login-benefits">
            <span>
              <Icon name="check" size={16} />
              Tồn kho từ dữ liệu thực
            </span>
            <span>
              <Icon name="check" size={16} />
              Phân quyền rõ ràng
            </span>
            <span>
              <Icon name="check" size={16} />
              Lịch sử đầy đủ
            </span>
          </div>
        </div>
        <span className="login-caption">
          SmartInventory AI · Một kho, một nguồn dữ liệu
        </span>
      </section>
      <section className="login-form-area">
        <form className="login-form" onSubmit={submit}>
          <span className="badge success">Kho chính</span>
          <h2>Chào mừng trở lại.</h2>
          <p>Đăng nhập để truy cập không gian làm việc của bạn.</p>
          <label>
            Email
            <input
              type="email"
              name="email"
              autoComplete="username"
              placeholder="Email tài khoản của bạn"
              required
              autoFocus
              disabled={busy}
            />
          </label>
          <label>
            Mật khẩu
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              placeholder="Nhập mật khẩu"
              required
              disabled={busy}
            />
          </label>
          {(error || message) && (
            <p className="error-banner" role="alert">
              {error || message}
            </p>
          )}
          <button className="button primary" disabled={busy}>
            {busy ? "Đang đăng nhập…" : "Đăng nhập"}
            <Icon name="arrow" size={18} />
          </button>
          <p className="login-help">
            Tài khoản do quản trị viên cấp. Liên hệ quản trị viên nếu bạn cần quyền truy
            cập.
          </p>
        </form>
      </section>
    </div>
  );
}
