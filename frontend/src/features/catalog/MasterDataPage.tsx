import { useCallback, useState } from "react";
import { errorMessage } from "../../shared/api/errors";
import type { Category, Supplier, User } from "../../shared/contracts";
import { useResource } from "../../shared/hooks/useResource";
import { Empty, Failure, Loading } from "../../shared/ui/Feedback";
import { Pagination } from "../../shared/ui/Pagination";
import type { Action } from "../operations/types";
import { fetchMasterData, setMasterDataActive } from "./api";

export function MasterData({
  kind,
  user,
  version,
  action,
  refresh,
  notify,
}: {
  kind: "category" | "supplier";
  user: User;
  version: number;
  action: (action: Action) => void;
  refresh: () => void;
  notify: (message: string) => void;
}) {
  const [page, setPage] = useState(1);
  const [mutationError, setMutationError] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const load = useCallback(
    (signal: AbortSignal) => fetchMasterData(kind, page, signal),
    [kind, page],
  );
  const { data, error } = useResource(load, version);
  async function toggle(item: Category | Supplier) {
    setPending(item.id);
    setMutationError("");
    try {
      await setMasterDataActive(kind, item.id, !item.is_active);
      notify("Đã cập nhật trạng thái.");
      refresh();
    } catch (error) {
      setMutationError(errorMessage(error));
    } finally {
      setPending(null);
    }
  }
  function edit(item: Category | Supplier) {
    if (kind === "category") action({ kind: "category", item });
    else if ("phone" in item) action({ kind: "supplier", item });
  }
  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>{kind === "category" ? "Danh mục sản phẩm" : "Danh sách nhà cung cấp"}</h2>
          <p>Dữ liệu dùng chung cho toàn bộ kho.</p>
        </div>
      </header>
      {mutationError && (
        <p className="error-banner" role="alert">
          {mutationError}
        </p>
      )}
      {error && <Failure message={error} retry={refresh} />}
      {!data && !error ? (
        <Loading />
      ) : (
        data && (
          <>
            {data.items.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Tên</th>
                      {kind === "supplier" && (
                        <>
                          <th>Điện thoại</th>
                          <th>Email</th>
                        </>
                      )}
                      <th>Trạng thái</th>
                      <th>Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <strong>{item.name}</strong>
                        </td>
                        {kind === "supplier" && (
                          <>
                            <td>{"phone" in item ? (item.phone ?? "—") : "—"}</td>
                            <td>{"email" in item ? (item.email ?? "—") : "—"}</td>
                          </>
                        )}
                        <td>
                          <span
                            className={`badge ${item.is_active ? "success" : "soft"}`}
                          >
                            {item.is_active ? "Hoạt động" : "Ngừng hoạt động"}
                          </span>
                        </td>
                        <td>
                          {user.role === "ADMIN" ? (
                            <div className="row-actions">
                              <button className="small-button" onClick={() => edit(item)}>
                                Chỉnh sửa
                              </button>
                              <button
                                disabled={pending !== null}
                                className="small-button"
                                onClick={() => void toggle(item)}
                              >
                                {pending === item.id
                                  ? "Đang lưu…"
                                  : item.is_active
                                    ? "Ngừng hoạt động"
                                    : "Kích hoạt"}
                              </button>
                            </div>
                          ) : (
                            <span className="muted">Chỉ đọc</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty
                title={kind === "category" ? "Chưa có danh mục" : "Chưa có nhà cung cấp"}
                description="Thêm dữ liệu để việc phân loại và nhập hàng dễ dàng hơn."
              />
            )}
            <Pagination page={page} total={data.total} change={setPage} />
          </>
        )
      )}
    </section>
  );
}
