from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / "frontend" / "src"


def read(name):
    return (root / name).read_text(encoding="utf-8")


def write(name, source):
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(source, encoding="utf-8")


workspace = read("app/Workspace.tsx")
login = workspace[workspace.index("function Login("):workspace.index("export default function App")]
login = re.sub(r"function Login\([\s\S]*?\) \{", '''export default function LoginPage({ login, message }: {
  login: (credentials: Credentials) => Promise<void>; message: string;
}) {''', login, count=1)
start = login.index("  async function login(")
end = login.index("  return (", start)
login = login[:start] + '''  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try { await login({ email: String(data.get("email") ?? ""), password: String(data.get("password") ?? "") }); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
''' + login[end:]
login = login.replace("onSubmit={login}", "onSubmit={submit}")
login = login.replace("Tồn kho theo thời gian thực", "Tồn kho từ dữ liệu thực")
write("features/auth/LoginPage.tsx", '''import { useState } from "react";
import type { FormEvent } from "react";
import type { Credentials } from "./api";
import { errorMessage } from "../../shared/api/errors";
import Icon from "../../shared/ui/Icon";

''' + login)

workspace = workspace[workspace.index("export default function App"):]
workspace = workspace.replace("export default function App()", "export default function Workspace({ user, logout }: { user: User; logout: () => void })")
workspace = re.sub(r'  const \[user, setUser\][^\n]+\n', "", workspace)
workspace = re.sub(r'  const \[authLoading, setAuthLoading\][^\n]+\n', "", workspace)
workspace = re.sub(r'  const \[authMessage, setAuthMessage\][^\n]+\n', "", workspace)
workspace = workspace.replace('useState("Tổng quan")', 'useState<ScreenId>("dashboard")')
for state in ("draft", "preset", "rangeError"):
    workspace = re.sub(rf'  const \[{state},[^\n]+\n', "", workspace)
start = workspace.index("  useEffect(() => {\n    if (getToken())")
end = workspace.index("  useEffect(() => {", start + 10)
workspace = workspace[:start] + workspace[end:]
start = workspace.index("  function applyDates(")
end = workspace.index("  const isAdmin", start)
workspace = workspace[:start] + workspace[end:]
start = workspace.index("  const isAdmin")
end = workspace.index("\n  return (", start)
workspace = workspace[:start] + '''  const details = screenDetails(screen);
  const role = roleLabels[user.role];
  const hasRange = screen === "dashboard" || screen === "movements";
  const primaryAction = primaryActionFor(screen, user);
  const actionLabel = primaryAction ? actionLabels[primaryAction.kind] : "";
''' + workspace[end:]
workspace = workspace.replace("function navigate(next: string", "function navigate(next: ScreenId")
workspace = workspace.replace('`SmartInventory — ${user ? screen : "Đăng nhập"}`', '`SmartInventory — ${screenDetails(screen).label}`')

# Extract layout elements without changing their HTML structure or class contracts.
start = workspace.index("<aside className=")
end = workspace.index("</aside>", start) + len("</aside>")
sidebar = workspace[start:end].replace("screen === item.label", "screen === item.id").replace("navigate(item.label)", "navigate(item.id)")
sidebar = sidebar.replace('navigate("Tổng quan")', 'navigate("dashboard")')
write("app/components/Sidebar.tsx", '''import type { User } from "../../shared/contracts";
import Icon from "../../shared/ui/Icon";
import { navigation, roleLabels } from "../navigation";
import type { Navigate, ScreenId } from "../navigation";

export default function Sidebar({ user, screen, mobile, navigate, logout }: {
  user: User; screen: ScreenId; mobile: boolean; navigate: Navigate; logout: () => void;
}) {
  const role = roleLabels[user.role];
  return (''' + sidebar + ");\n}\n")
workspace = workspace[:start] + '<Sidebar user={user} screen={screen} mobile={mobile} navigate={navigate} logout={logout} />' + workspace[end:]
start = workspace.index('<header className="topbar">')
end = workspace.index("</header>", start) + len("</header>")
topbar = workspace[start:end].replace("{screen}", "{label}").replace("onClick={() => setMobile(!mobile)}", "onClick={toggleMenu}")
topbar = topbar.replace("Asia/Ho_Chi_Minh · VND", "Giờ Việt Nam · VND")
write("app/components/Topbar.tsx", '''import Icon from "../../shared/ui/Icon";
export default function Topbar({ label, role, mobile, toggleMenu }: {
  label: string; role: string; mobile: boolean; toggleMenu: () => void;
}) { return (''' + topbar + "); }\n")
workspace = workspace[:start] + '<Topbar label={details.label} role={role} mobile={mobile} toggleMenu={() => setMobile(value => !value)} />' + workspace[end:]
start = workspace.index('<div className="page-heading">')
end = workspace.index("{hasRange &&", start)
heading = workspace[start:end].strip()
heading = heading.replace('{screen === "Tổng quan" ? "Tổng quan kho hàng" : screen}', '{title}').replace("{descriptions[screen]}", "{description}")
write("app/components/PageHeader.tsx", '''import Icon from "../../shared/ui/Icon";
import type { Action } from "../../features/operations/types";
export default function PageHeader({ title, description, primaryAction, actionLabel, refresh, setAction }: {
  title: string; description: string; primaryAction: Action | null; actionLabel: string;
  refresh: () => void; setAction: (action: Action) => void;
}) { return (''' + heading + "); }\n")
workspace = workspace[:start] + '<PageHeader title={screen === "dashboard" ? "Tổng quan kho hàng" : details.label} description={details.description} primaryAction={primaryAction} actionLabel={actionLabel} refresh={refresh} setAction={setAction} />\n          ' + workspace[end:]
start = workspace.index("{hasRange &&")
end = workspace.index('{screen === "Tổng quan"', start)
range_block = workspace[start:end]
form_start = range_block.index('<form className="range-toolbar"')
form_end = range_block.index("</form>", form_start) + len("</form>")
form = range_block[form_start:form_end].replace("setRange(next)", "onChange(next)")
error_markup = range_block[range_block.index("{rangeError &&"):range_block.rindex("</>")].strip()
write("app/components/ReportPeriod.tsx", '''import { useState } from "react";
import type { FormEvent } from "react";
import type { Range } from "../../shared/contracts";
import { isValidRange, rangeFor } from "../../shared/lib/dates";
import Icon from "../../shared/ui/Icon";

export default function ReportPeriod({ range, onChange }: { range: Range; onChange: (range: Range) => void }) {
  const [draft, setDraft] = useState(range);
  const [preset, setPreset] = useState("30");
  const [rangeError, setRangeError] = useState("");
  function applyDates(event: FormEvent) {
    event.preventDefault();
    if (!isValidRange(draft)) { setRangeError("Chọn khoảng ngày hợp lệ, tối đa 366 ngày."); return; }
    setRangeError(""); onChange({ ...draft });
  }
  return (<>''' + form + error_markup + "</>);\n}\n")
workspace = workspace[:start] + '{hasRange && <ReportPeriod range={range} onChange={setRange} />}\n          ' + workspace[end:]

for label, screen in (("Tổng quan", "dashboard"), ("Sản phẩm", "products"), ("Danh mục", "categories"), ("Nhà cung cấp", "suppliers"), ("Giao dịch kho", "movements")):
    workspace = workspace.replace(f'screen === "{label}"', f'screen === "{screen}"')
workspace = workspace.replace("navigate={navigate}", "navigate={navigate}")
workspace = workspace.replace('              navigate={navigate}\n              refresh=', '              viewProducts={(low = false) => navigate("products", low)}\n              viewHistory={() => navigate("movements")}\n              refresh=')
header = '''import { useCallback, useEffect, useState } from "react";
import type { Range, User } from "../shared/contracts";
import type { Action } from "../features/operations/types";
import OperationDialog from "../features/operations/OperationDialog";
import Icon from "../shared/ui/Icon";
import Dashboard from "../features/dashboard/DashboardPage";
import { Products } from "../features/catalog/ProductsPage";
import { MasterData } from "../features/catalog/MasterDataPage";
import History from "../features/inventory/HistoryPage";
import { rangeFor } from "../shared/lib/dates";
import { actionLabels, primaryActionFor, roleLabels, screenDetails } from "./navigation";
import type { ScreenId } from "./navigation";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import PageHeader from "./components/PageHeader";
import ReportPeriod from "./components/ReportPeriod";
'''
workspace = workspace.replace("<Dialog", "<OperationDialog").replace("const refresh = () => setVersion((value) => value + 1);", "const refresh = useCallback(() => setVersion(value => value + 1), []);")
write("app/Workspace.tsx", header + "\n" + workspace)

# Read screens use a single cancellation-safe resource hook instead of repeated effects.
target = "features/dashboard/DashboardPage.tsx"
code = read(target)
code = re.sub(r'import \{ useEffect, useState \} from "react";', 'import { useCallback, useState } from "react";', code)
code = re.sub(r'import \{ api, errorMessage, query \} from [^;]+;\n', "", code)
code = code.replace("  navigate,", "  viewProducts,\n  viewHistory,")
code = code.replace("  navigate: (screen: string, low?: boolean) => void;", "  viewProducts: (low?: boolean) => void;\n  viewHistory: () => void;")
start = code.index("  const [data, setData]")
end = code.index("  if (error)", start)
code = code[:start] + '''  const [unit, setUnit] = useState("PCS");
  const load = useCallback((signal: AbortSignal) => fetchDashboard(range, signal), [range]);
  const { data, error } = useResource(load, version);
''' + code[end:]
code = code.replace('navigate("Sản phẩm", true)', "viewProducts(true)").replace('navigate("Sản phẩm")', "viewProducts()").replace('navigate("Giao dịch kho")', "viewHistory()")
code = code.replace("Dữ liệu PostgreSQL", "Dữ liệu kho")
code = re.sub(r"S\? li\?u t\?n[^<\n]+", "Số liệu tồn là hiện tại; khoảng ngày áp dụng cho giao dịch và biểu đồ.", code)
write(target, 'import { useResource } from "../../shared/hooks/useResource";\nimport { fetchDashboard } from "./api";\n' + code)

target = "features/catalog/ProductsPage.tsx"
code = read(target).replace('import { useEffect, useState }', 'import { useCallback, useState }')
code = re.sub(r'import \{ allPages, api, errorMessage, query \} from [^;]+;\n', "", code)
code = code.replace('  const [debounced, setDebounced] = useState("");', '  const debounced = useDebouncedValue(search);')
start = code.index("  const [data, setData]")
end = code.index("\n  return (", start)
code = code[:start] + '''  const load = useCallback(async (signal: AbortSignal) => {
    const [data, categories] = await Promise.all([
      fetchProducts({ search: debounced, page, active, low_stock: low, category_id: category }, signal),
      fetchCategories(signal),
    ]);
    return { data, categories };
  }, [debounced, page, active, low, category]);
  const resource = useResource(load, version);
  const data = resource.data?.data ?? null;
  const categories = resource.data?.categories ?? [];
  const error = resource.error;
''' + code[end:]
code = code.replace('onChange={(e) => setSearch(e.target.value)}', 'onChange={(e) => { setSearch(e.target.value); setPage(1); }}')
write(target, '''import { useResource } from "../../shared/hooks/useResource";
import { useDebouncedValue } from "../../shared/hooks/useDebouncedValue";
import { fetchCategories, fetchProducts } from "./api";
''' + code)

target = "features/inventory/HistoryPage.tsx"
code = read(target).replace('import { useEffect, useState }', 'import { useCallback, useState }')
code = re.sub(r'import \{ api, errorMessage, query \} from [^;]+;\n', "", code)
code = code.replace('  const [search, setSearch] = useState("");', '  const search = useDebouncedValue(sku);')
code = code.replace('  const [type, setType] = useState("");', '  const [type, setType] = useState<MovementType | "">("");')
start = code.index("  const [data, setData]")
end = code.index("\n  return (", start)
code = code[:start] + '''  const load = useCallback((signal: AbortSignal) => fetchMovements({ ...range, sku: search, movement_type: type, page }, signal), [range, search, type, page]);
  const { data, error } = useResource(load, version);
''' + code[end:]
code = code.replace('onChange={(e) => setSku(e.target.value)}', 'onChange={(e) => { setSku(e.target.value); setPage(1); }}')
code = code.replace("setType(e.target.value)", "setType(e.target.value as MovementType | \"\")")
write(target, '''import { useResource } from "../../shared/hooks/useResource";
import { useDebouncedValue } from "../../shared/hooks/useDebouncedValue";
import type { MovementType } from "../../shared/contracts";
import { fetchMovements } from "./api";
''' + code)

# All action contracts are imported as types, never through the dialog component module.
for path in root.rglob("*.tsx"):
    code = path.read_text(encoding="utf-8")
    code = re.sub(r'(import type \{ Action \} from ".*)OperationDialog(";)', r'\1types\2', code)
    path.write_text(code, encoding="utf-8")
