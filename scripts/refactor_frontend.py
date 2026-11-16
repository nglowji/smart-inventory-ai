"""One-shot source relocation preserving existing JSX; removed after the refactor."""
from pathlib import Path
import os
import re

root = Path(__file__).resolve().parents[1] / "frontend" / "src"
original = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8-sig")
            for p in root.rglob("*") if p.is_file()}
mapping = {
    "App.tsx": "app/Workspace.tsx",
    "api.ts": "shared/api/client.ts",
    "types.ts": "shared/contracts.ts",
    "format.ts": "shared/lib/format.ts",
    "components/Icon.tsx": "shared/ui/Icon.tsx",
    "components/Common.tsx": "shared/ui/Feedback.tsx",
    "components/Dialog.tsx": "features/operations/OperationDialog.tsx",
    "components/FlowChart.tsx": "features/dashboard/FlowChart.tsx",
    "screens/Dashboard.tsx": "features/dashboard/DashboardPage.tsx",
    "screens/History.tsx": "features/inventory/HistoryPage.tsx",
    "screens/Catalog.tsx": "features/catalog/ProductsPage.tsx",
}


def relative(target, dependency):
    value = os.path.relpath(root / dependency, (root / target).parent).replace("\\", "/")
    value = re.sub(r"\.(tsx?|jsx?)$", "", value)
    return value if value.startswith(".") else "./" + value


def rewrite(code, source, target):
    def replace(match):
        path = match[2]
        resolved = (root / source).parent.joinpath(path).resolve()
        key = resolved.relative_to(root.resolve()).as_posix()
        key = next((candidate for candidate in (key, key + ".ts", key + ".tsx")
                    if candidate in mapping), key)
        return match[1] + relative(target, mapping.get(key, key)) + match[3]
    return re.sub(r'(from\s+["\']|import\s+["\'])(\.[^"\']+)(["\'])', replace, code)


def write(target, code):
    path = root / target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")


common = original["components/Common.tsx"]
feedback = common[common.index("export function Empty"):common.index("export function Pagination")]
pagination = common[common.index("export function Pagination"):common.index("export function MovementsTable")]
movement_table = common[common.index("export function MovementsTable"):common.index("export function downloadCsv")]
csv = common[common.index("export function downloadCsv"):]
write("shared/ui/Feedback.tsx", 'import type { ReactNode } from "react";\nimport Icon from "./Icon";\n' + feedback.replace("React.ReactNode", "ReactNode"))
write("shared/ui/Pagination.tsx", pagination)
write("shared/lib/csv.ts", csv)
write("features/inventory/MovementsTable.tsx", 'import type { Movement } from "../../shared/contracts";\nimport { dateTime, movementNames, quantity } from "../../shared/lib/format";\n' + movement_table)

for source, target in mapping.items():
    if source == "components/Common.tsx":
        continue
    code = original[source]
    if source == "screens/Catalog.tsx":
        header = code[:code.index("export function Products")]
        master = code[code.index("export function MasterData"):]
        write("features/catalog/MasterDataPage.tsx", rewrite(header + master, source, "features/catalog/MasterDataPage.tsx"))
        code = code[:code.index("export function MasterData")]
    write(target, rewrite(code, source, target))

# Move generic/domain helpers out of the shared UI module's import sites.
for path in root.rglob("*.tsx"):
    if path.relative_to(root).as_posix() in original:
        continue
    target = path.relative_to(root).as_posix()
    code = path.read_text(encoding="utf-8")
    additions = []
    def imports(match):
        names = [part.strip() for part in match[1].split(",") if part.strip()]
        for name, dependency in (("Pagination", "shared/ui/Pagination.tsx"),
                                  ("downloadCsv", "shared/lib/csv.ts"),
                                  ("MovementsTable", "features/inventory/MovementsTable.tsx")):
            if name in names:
                names.remove(name)
                additions.append(f'import {{ {name} }} from "{relative(target, dependency)}";\n')
        return f'import {{ {", ".join(names)} }} from "{match[2]}";' if names else ""
    code = re.sub(r'import\s*\{([^}]+)\}\s*from\s*["\']([^"\']*Feedback)["\'];?', imports, code)
    write(target, "".join(additions) + code)

# Split CSS by responsibility. Preserve rule order inside each group; media overrides stay last.
css = original["styles.css"]
groups = {name: [] for name in ("tokens", "base", "layout", "components", "forms", "dashboard", "auth", "responsive")}
start, depth = 0, 0
for index, char in enumerate(css):
    if char == "{": depth += 1
    elif char == "}":
        depth -= 1
        if depth == 0:
            rule = css[start:index + 1].strip()
            start = index + 1
            selector = rule.partition("{")[0].strip()
            if selector.startswith("@media"): group = "responsive"
            elif selector.startswith(":root"): group = "tokens"
            elif selector.startswith(".login"): group = "auth"
            elif re.search(r"\.(modal|form-fields|form-row|form-help|balance-preview|archive-note)", selector): group = "forms"
            elif re.search(r"\.(data-context|metric-grid|kpi|dashboard|flow-|chart-|low-|stock-|recent-panel)", selector): group = "dashboard"
            elif re.search(r"\.(sidebar|wordmark|workspace|nav-|avatar|topbar|breadcrumb|crumb-|page-|heading-|range-|date-inputs|mobile-|menu-backdrop)", selector): group = "layout"
            elif not selector.startswith(".") and not selector.startswith("@"): group = "base"
            else: group = "components"
            groups[group].append(rule)
for name, rules in groups.items():
    write(f"shared/styles/{name}.css", "\n\n".join(rules) + "\n")
write("shared/styles/index.css", "\n".join(f'@import "./{name}.css";' for name in groups) + "\n")

# Main entry imports the composition root, not the workspace implementation.
main = original["main.tsx"].replace('"./App"', '"./app/App"').replace('"./styles.css"', '"./shared/styles/index.css"')
write("main.tsx", main)
for source in mapping:
    (root / source).unlink()
(root / "styles.css").unlink()
