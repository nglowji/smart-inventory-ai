import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, errorMessage, getToken, setToken } from "./api";
import { localDate } from "./format";
import type { Range, User } from "./types";
import Dialog from "./components/Dialog";
import type { Action } from "./components/Dialog";
import Icon from "./components/Icon";
import Dashboard from "./screens/Dashboard";
import { MasterData, Products } from "./screens/Catalog";
import History from "./screens/History";
import { Loading } from "./components/Common";

const navigation = [
  { label: "Tổng quan", icon: "overview" },
  { label: "Sản phẩm", icon: "box" },
  { label: "Danh mục", icon: "list" },
  { label: "Nhà cung cấp", icon: "truck" },
  { label: "Giao dịch kho", icon: "activity" },
] as const;
const descriptions: Record<string, string> = {
  "Tổng quan": "Tình hình kho hàng, cảnh báo và hoạt động trong một góc nhìn.",
  "Sản phẩm": "Quản lý danh mục hàng hóa và tồn kho theo từng SKU.",
  "Danh mục": "Sắp xếp sản phẩm thành những nhóm dễ quản lý.",
  "Nhà cung cấp": "Thông tin đối tác cung ứng hàng hóa cho kho.",
  "Giao dịch kho": "Theo dõi từng lần nhập, xuất và điều chỉnh tồn kho.",
};
function rangeFor(days: number): Range {
  const end = localDate(new Date());
  const start = new Date(`${end}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - days + 1);
  return { date_from: start.toISOString().slice(0, 10), date_to: end };
}

function Login({
  authenticated,
  message,
}: {
  authenticated: (user: User) => void;
  message: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
        }),
      });
      setToken(result.access_token);
      const user = await api<User>("/auth/me");
      authenticated(user);
    } catch (err) {
      setToken(null);
      setError(errorMessage(err));
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
            Quản lý tồn kho chính xác, truy vết từng giao dịch và luôn biết khi
            nào cần bổ sung hàng.
          </p>
          <div className="login-benefits">
            <span>
              <Icon name="check" size={16} />
              Tồn kho theo thời gian thực
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
        <form className="login-form" onSubmit={login}>
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
            Tài khoản do quản trị viên cấp. Liên hệ quản trị viên nếu bạn cần
            quyền truy cập.
          </p>
        </form>
      </section>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(Boolean(getToken()));
  const [authMessage, setAuthMessage] = useState("");
  const [screen, setScreen] = useState("Tổng quan");
  const [initialLow, setInitialLow] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [range, setRange] = useState<Range>(() => rangeFor(30));
  const [draft, setDraft] = useState(range);
  const [preset, setPreset] = useState("30");
  const [rangeError, setRangeError] = useState("");
  const [version, setVersion] = useState(0);
  const [action, setAction] = useState<Action | null>(null);
  const [toast, setToast] = useState("");
  const refresh = () => setVersion((value) => value + 1);
  useEffect(() => {
    if (getToken())
      void api<User>("/auth/me")
        .then(setUser)
        .catch((err) => {
          setToken(null);
          setAuthMessage(errorMessage(err));
        })
        .finally(() => setAuthLoading(false));
    const expired = () => {
      setUser(null);
      setAction(null);
      setAuthMessage("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  useEffect(() => {
    document.title = `SmartInventory — ${user ? screen : "Đăng nhập"}`;
  }, [screen, user]);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 6000);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  function navigate(next: string, low = false) {
    setScreen(next);
    setInitialLow(low);
    setMobile(false);
  }
  function applyDates(event: FormEvent) {
    event.preventDefault();
    const difference =
      (Date.parse(draft.date_to) - Date.parse(draft.date_from)) / 86400000;
    if (!Number.isFinite(difference) || difference < 0 || difference > 365) {
      setRangeError("Chọn khoảng ngày hợp lệ, tối đa 366 ngày.");
      return;
    }
    setRangeError("");
    setRange({ ...draft });
  }
  function logout() {
    setToken(null);
    setUser(null);
    setAction(null);
    setAuthMessage("");
  }
  if (authLoading)
    return (
      <div className="boot-screen">
        <Loading />
      </div>
    );
  if (!user)
    return (
      <Login
        authenticated={(value) => {
          setUser(value);
          setAuthMessage("");
          refresh();
        }}
        message={authMessage}
      />
    );
  const isAdmin = user.role === "ADMIN";
  const canWrite = user.role !== "VIEWER";
  const role = {
    ADMIN: "Quản trị viên",
    STAFF: "Nhân viên kho",
    VIEWER: "Chỉ xem",
  }[user.role];
  const hasRange = screen === "Tổng quan" || screen === "Giao dịch kho";
  const primaryAction: Action | null =
    screen === "Danh mục" && isAdmin
      ? { kind: "category" }
      : screen === "Nhà cung cấp" && isAdmin
        ? { kind: "supplier" }
        : screen === "Sản phẩm" && isAdmin
          ? { kind: "product" }
          : canWrite && (screen === "Tổng quan" || screen === "Giao dịch kho")
            ? { kind: "movement" }
            : null;
  const actionLabel =
    primaryAction?.kind === "category"
      ? "Thêm danh mục"
      : primaryAction?.kind === "supplier"
        ? "Thêm nhà cung cấp"
        : primaryAction?.kind === "product"
          ? "Thêm sản phẩm"
          : "Tạo giao dịch";

  return (
    <div className="app live-app">
      <a className="skip-link" href="#main-content">
        Đến nội dung chính
      </a>
      {mobile && (
        <button
          className="menu-backdrop"
          aria-label="Đóng menu"
          onClick={() => setMobile(false)}
        />
      )}
      <aside className={`sidebar ${mobile ? "is-open" : ""}`}>
        <a
          href="#main-content"
          className="wordmark"
          onClick={() => navigate("Tổng quan")}
        >
          Smart<span>Inventory</span>
          <span className="wordmark-ai">AI</span>
        </a>
        <div className="workspace">
          <div className="workspace-mark">
            <Icon name="box" size={19} />
          </div>
          <div>
            <strong>Kho chính</strong>
            <span>Không gian làm việc</span>
          </div>
        </div>
        <p className="nav-label">VẬN HÀNH</p>
        <nav aria-label="Điều hướng chính">
          {navigation.map((item) => (
            <button
              className={`nav-item ${screen === item.label ? "active" : ""}`}
              aria-current={screen === item.label ? "page" : undefined}
              key={item.label}
              onClick={() => navigate(item.label)}
            >
              <Icon name={item.icon} size={19} />
              <span>{item.label}</span>
              {screen === item.label && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <Icon name="check" size={17} />
          <div>
            <strong>Dữ liệu tập trung</strong>
            <p>Mọi thay đổi được lưu trực tiếp vào kho của bạn.</p>
          </div>
        </div>
        <div className="sidebar-user">
          <div className="avatar">{user.email.slice(0, 2).toUpperCase()}</div>
          <div>
            <strong title={user.email}>{user.email}</strong>
            <span>{role}</span>
          </div>
          <button
            className="icon-button"
            onClick={logout}
            aria-label="Đăng xuất"
            title="Đăng xuất"
          >
            <Icon name="logout" size={17} />
          </button>
        </div>
      </aside>
      <div className="workspace-content">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-toggle"
              onClick={() => setMobile(!mobile)}
              aria-label="Mở menu"
              aria-expanded={mobile}
            >
              <Icon name="menu" />
            </button>
            <span>Kho chính</span>
            <span className="crumb-divider">/</span>
            <strong>{screen}</strong>
          </div>
          <div className="topbar-right">
            <span className="topbar-caption">Asia/Ho_Chi_Minh · VND</span>
            <span className="badge soft">{role}</span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <p className="page-kicker">KHÔNG GIAN LÀM VIỆC</p>
              <h1>{screen === "Tổng quan" ? "Tổng quan kho hàng" : screen}</h1>
              <p className="page-description">{descriptions[screen]}</p>
            </div>
            <div className="heading-actions">
              <button className="button" onClick={refresh}>
                <Icon name="refresh" size={16} />
                Làm mới
              </button>
              {primaryAction && (
                <button
                  className="button primary"
                  onClick={() => setAction(primaryAction)}
                >
                  <Icon name="plus" size={17} />
                  {actionLabel}
                </button>
              )}
            </div>
          </div>
          {hasRange && (
            <>
              <form className="range-toolbar" onSubmit={applyDates}>
                <div className="range-description">
                  <Icon name="activity" size={18} />
                  <span>Kỳ báo cáo</span>
                </div>
                <select
                  aria-label="Khoảng ngày nhanh"
                  value={preset}
                  onChange={(e) => {
                    setPreset(e.target.value);
                    if (e.target.value !== "custom") {
                      const next = rangeFor(Number(e.target.value));
                      setRange(next);
                      setDraft(next);
                      setRangeError("");
                    }
                  }}
                >
                  <option value="7">7 ngày gần nhất</option>
                  <option value="30">30 ngày gần nhất</option>
                  <option value="90">90 ngày gần nhất</option>
                  <option value="custom">Tùy chọn</option>
                </select>
                <div className="date-inputs">
                  <label>
                    <span className="sr-only">Từ ngày</span>
                    <input
                      type="date"
                      required
                      value={draft.date_from}
                      onChange={(e) => {
                        setDraft({ ...draft, date_from: e.target.value });
                        setPreset("custom");
                      }}
                    />
                  </label>
                  <span>—</span>
                  <label>
                    <span className="sr-only">Đến ngày</span>
                    <input
                      type="date"
                      required
                      value={draft.date_to}
                      onChange={(e) => {
                        setDraft({ ...draft, date_to: e.target.value });
                        setPreset("custom");
                      }}
                    />
                  </label>
                  <button className="button" type="submit">
                    Áp dụng
                  </button>
                </div>
                <span className="range-hint">Giờ Việt Nam (UTC+7)</span>
              </form>
              {rangeError && (
                <p className="error-banner" role="alert">
                  {rangeError}
                </p>
              )}
            </>
          )}
          {screen === "Tổng quan" && (
            <Dashboard
              range={range}
              version={version}
              user={user}
              action={setAction}
              navigate={navigate}
              refresh={refresh}
            />
          )}
          {screen === "Sản phẩm" && (
            <Products
              key={String(initialLow)}
              initialLow={initialLow}
              user={user}
              version={version}
              action={setAction}
              refresh={refresh}
            />
          )}
          {screen === "Danh mục" && (
            <MasterData
              key="categories"
              kind="category"
              user={user}
              version={version}
              action={setAction}
              refresh={refresh}
              notify={setToast}
            />
          )}
          {screen === "Nhà cung cấp" && (
            <MasterData
              key="suppliers"
              kind="supplier"
              user={user}
              version={version}
              action={setAction}
              refresh={refresh}
              notify={setToast}
            />
          )}
          {screen === "Giao dịch kho" && (
            <History
              key={JSON.stringify(range)}
              range={range}
              version={version}
              refresh={refresh}
            />
          )}
          <footer className="page-footer">
            <span>SmartInventory AI</span>
            <span>
              Giá trị tồn kho là ước tính, không thay thế số liệu kế toán.
            </span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={18} />
          <span>{toast}</span>
          <button
            className="icon-button"
            aria-label="Đóng thông báo"
            onClick={() => setToast("")}
          >
            <Icon name="close" size={16} />
          </button>
        </div>
      )}
      {action && (
        <Dialog
          action={action}
          user={user}
          close={() => setAction(null)}
          saved={(message) => {
            setAction(null);
            setToast(message);
            refresh();
          }}
        />
      )}
    </div>
  );
}
