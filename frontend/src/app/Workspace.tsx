import { useCallback, useEffect, useState } from "react";
import { MasterData } from "../features/catalog/MasterDataPage";
import { Products } from "../features/catalog/ProductsPage";
import Dashboard from "../features/dashboard/DashboardPage";
import History from "../features/inventory/HistoryPage";
import UsersPage from "../features/users/UsersPage";
import AuditPage from "../features/audit/AuditPage";
import AssistantPage from "../features/assistant/AssistantPage";
import OperationDialog from "../features/operations/OperationDialog";
import type { Action } from "../features/operations/types";
import type { Range, User } from "../shared/contracts";
import { rangeFor } from "../shared/lib/dates";
import { roleLabels } from "../shared/lib/roles";
import Icon from "../shared/ui/Icon";
import PageHeader from "./components/PageHeader";
import ReportPeriod from "./components/ReportPeriod";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import type { ScreenId } from "./navigation";
import { actionLabels, primaryActionFor, screenDetails } from "./navigation";

export default function Workspace({ user, logout }: { user: User; logout: () => void }) {
  const [screen, setScreen] = useState<ScreenId>("dashboard");
  const [initialLow, setInitialLow] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [range, setRange] = useState<Range>(() => rangeFor(30));
  const [version, setVersion] = useState(0);
  const [action, setAction] = useState<Action | null>(null);
  const [toast, setToast] = useState("");
  const refresh = useCallback(() => setVersion((value) => value + 1), []);
  useEffect(() => {
    document.title = `SmartInventory — ${screenDetails(screen).label}`;
  }, [screen, user]);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 6000);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  function navigate(next: ScreenId, low = false) {
    setScreen(next);
    setInitialLow(low);
    setMobile(false);
  }
  const details = screenDetails(screen);
  const role = roleLabels[user.role];
  const hasRange = screen === "dashboard" || screen === "movements" || screen === "audit";
  const primaryAction = primaryActionFor(screen, user);
  const actionLabel = primaryAction ? actionLabels[primaryAction.kind] : "";

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
      <Sidebar
        user={user}
        screen={screen}
        mobile={mobile}
        navigate={navigate}
        logout={logout}
        changePassword={() => setAction({ kind: "password" })}
      />
      <div className="workspace-content">
        <Topbar
          label={details.label}
          role={role}
          mobile={mobile}
          toggleMenu={() => setMobile((value) => !value)}
        />
        <main id="main-content" tabIndex={-1}>
          <PageHeader
            title={screen === "dashboard" ? "Tổng quan kho hàng" : details.label}
            description={details.description}
            primaryAction={primaryAction}
            actionLabel={actionLabel}
            refresh={refresh}
            setAction={setAction}
          />
          {hasRange && <ReportPeriod range={range} onChange={setRange} />}
          {screen === "dashboard" && (
            <Dashboard
              range={range}
              version={version}
              user={user}
              action={setAction}
              viewProducts={(low = false) => navigate("products", low)}
              viewHistory={() => navigate("movements")}
              refresh={refresh}
            />
          )}
          {screen === "products" && (
            <Products
              key={String(initialLow)}
              initialLow={initialLow}
              user={user}
              version={version}
              action={setAction}
              refresh={refresh}
            />
          )}
          {screen === "categories" && (
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
          {screen === "suppliers" && (
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
          {screen === "movements" && (
            <History
              key={JSON.stringify(range)}
              range={range}
              version={version}
              refresh={refresh}
            />
          )}
          {screen === "users" && user.role === "ADMIN" && (
            <UsersPage
              version={version}
              refresh={refresh}
              currentUserId={user.id}
              edit={(account) => setAction({ kind: "account", account })}
            />
          )}
          {screen === "audit" && user.role === "ADMIN" && (
            <AuditPage
              key={JSON.stringify(range)}
              range={range}
              version={version}
              refresh={refresh}
            />
          )}
          {screen === "assistant" && <AssistantPage version={version} />}
          <footer className="page-footer">
            <span>SmartInventory AI</span>
            <span>Giá trị tồn kho là ước tính, không thay thế số liệu kế toán.</span>
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
        <OperationDialog
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
