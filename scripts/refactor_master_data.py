from pathlib import Path

path = Path(__file__).resolve().parents[1] / "frontend/src/features/catalog/MasterDataPage.tsx"
code = path.read_text(encoding="utf-8")
code = code.replace('import { useEffect, useState }', 'import { useCallback, useState }')
code = code.replace('import { allPages, api, errorMessage, query } from "../../shared/api/client";', 'import { errorMessage } from "../../shared/api/errors";')
start = code.index('  const [data, setData]')
end = code.index('  return (', start)
code = code[:start] + '''  const [page, setPage] = useState(1);
  const [mutationError, setMutationError] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const load = useCallback((signal: AbortSignal) => fetchMasterData(kind, page, signal), [kind, page]);
  const { data, error } = useResource(load, version);
  async function toggle(item: Category | Supplier) {
    setPending(item.id); setMutationError("");
    try { await setMasterDataActive(kind, item.id, !item.is_active); notify("Đã cập nhật trạng thái."); refresh(); }
    catch (error) { setMutationError(errorMessage(error)); }
    finally { setPending(null); }
  }
  function edit(item: Category | Supplier) {
    if (kind === "category") action({ kind: "category", item });
    else if ("phone" in item) action({ kind: "supplier", item });
  }
''' + code[end:]
code = code.replace('{error && <Failure message={error} retry={refresh} />}', '{mutationError && <p className="error-banner" role="alert">{mutationError}</p>}{error && <Failure message={error} retry={refresh} />}')
start = code.index('                                onClick={() =>\n                                  action(')
end = code.index('                              >', start)
code = code[:start] + '                                onClick={() => edit(item)}\n' + code[end:]
code = code.replace('disabled={pending === item.id}', 'disabled={pending !== null}')
code = code.replace('{item.phone ?? "—"}', '{"phone" in item ? item.phone ?? "—" : "—"}').replace('{item.email ?? "—"}', '{"email" in item ? item.email ?? "—" : "—"}')
code = 'import { useResource } from "../../shared/hooks/useResource";\nimport { fetchMasterData, setMasterDataActive } from "./api";\n' + code
path.write_text(code, encoding="utf-8")
