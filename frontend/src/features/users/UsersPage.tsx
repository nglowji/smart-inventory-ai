import { useCallback, useState } from "react";
import type { ManagedUser } from "../../shared/contracts";
import { useDebouncedValue } from "../../shared/hooks/useDebouncedValue";
import { useResource } from "../../shared/hooks/useResource";
import { dateTime } from "../../shared/lib/format";
import { roleLabels } from "../../shared/lib/roles";
import { Empty, Failure, Loading } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import { Pagination } from "../../shared/ui/Pagination";
import { fetchUsers } from "./api";

export default function UsersPage({
  version,
  refresh,
  edit,
  currentUserId,
}: {
  version: number;
  refresh: () => void;
  edit: (user: ManagedUser) => void;
  currentUserId: string;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const term = useDebouncedValue(search);
  const load = useCallback(
    (signal: AbortSignal) => fetchUsers(page, term, signal),
    [page, term],
  );
  const { data, error } = useResource(load, version);
  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>Tài khoản và quyền truy cập</h2>
          <p>Admin quản trị hệ thống · Staff nhập/xuất · Viewer chỉ xem</p>
        </div>
      </header>
      <div className="toolbar">
        <label className="search-field">
          <Icon name="search" size={18} />
          <input
            aria-label="Tìm tài khoản theo email"
            placeholder="Tìm theo email…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>
      {error ? (
        <Failure message={error} retry={refresh} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          {data.items.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Vai trò</th>
                    <th>Trạng thái</th>
                    <th>Ngày tạo</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((account) => (
                    <tr key={account.id}>
                      <td>
                        <strong>{account.email}</strong>
                        {account.id === currentUserId && (
                          <span className="cell-sub">Tài khoản của bạn</span>
                        )}
                      </td>
                      <td>{roleLabels[account.role]}</td>
                      <td>
                        <span
                          className={`badge ${account.is_active ? "success" : "soft"}`}
                        >
                          {account.is_active ? "Hoạt động" : "Đã khóa"}
                        </span>
                      </td>
                      <td className="muted nowrap">{dateTime(account.created_at)}</td>
                      <td>
                        <button className="small-button" onClick={() => edit(account)}>
                          Quản lý
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Không tìm thấy tài khoản"
              description="Thử một email khác hoặc thêm tài khoản mới."
            />
          )}
          <Pagination total={data.total} page={page} change={setPage} />
        </>
      )}
    </section>
  );
}
