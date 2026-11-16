import type { User } from "../../shared/contracts";
import Icon from "../../shared/ui/Icon";
import type { Navigate, ScreenId } from "../navigation";
import { navigation, roleLabels } from "../navigation";

export default function Sidebar({
  user,
  screen,
  mobile,
  navigate,
  logout,
}: {
  user: User;
  screen: ScreenId;
  mobile: boolean;
  navigate: Navigate;
  logout: () => void;
}) {
  const role = roleLabels[user.role];
  return (
    <aside className={`sidebar ${mobile ? "is-open" : ""}`}>
      <a href="#main-content" className="wordmark" onClick={() => navigate("dashboard")}>
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
            className={`nav-item ${screen === item.id ? "active" : ""}`}
            aria-current={screen === item.id ? "page" : undefined}
            key={item.label}
            onClick={() => navigate(item.id)}
          >
            <Icon name={item.icon} size={19} />
            <span>{item.label}</span>
            {screen === item.id && <span className="nav-active-dot" />}
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
  );
}
