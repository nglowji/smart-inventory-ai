import { belowMinimum } from "./model";
import { useCallback, useState } from "react";
import type { User } from "../../shared/contracts";
import { useDebouncedValue } from "../../shared/hooks/useDebouncedValue";
import { useResource } from "../../shared/hooks/useResource";
import { downloadCsv } from "../../shared/lib/csv";
import { money, quantity } from "../../shared/lib/format";
import { Empty, Failure, Loading } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import { Pagination } from "../../shared/ui/Pagination";
import type { Action } from "../operations/types";
import { fetchCategories, fetchProducts } from "./api";

export function Products({
  user,
  version,
  initialLow,
  action,
  refresh,
}: {
  user: User;
  version: number;
  initialLow: boolean;
  action: (action: Action) => void;
  refresh: () => void;
}) {
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search);
  const [active, setActive] = useState("true");
  const [low, setLow] = useState(initialLow);
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [data, categories] = await Promise.all([
        fetchProducts(
          { search: debounced, page, active, low_stock: low, category_id: category },
          signal,
        ),
        fetchCategories(signal),
      ]);
      return { data, categories };
    },
    [debounced, page, active, low, category],
  );
  const resource = useResource(load, version);
  const data = resource.data?.data ?? null;
  const categories = resource.data?.categories ?? [];
  const error = resource.error;

  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>Danh sách sản phẩm</h2>
          <p>Mỗi SKU có một dòng tồn kho, không sửa số dư trực tiếp.</p>
        </div>
        <button
          className="button"
          disabled={!data?.items.length}
          onClick={() =>
            data &&
            downloadCsv(
              "san-pham-trang-hien-tai.csv",
              ["SKU", "Tên", "Đơn vị", "Tồn", "Tối thiểu", "Đơn giá (VND)"],
              data.items.map((p) => [
                p.sku,
                p.name,
                p.unit,
                p.on_hand,
                p.min_stock,
                p.unit_cost_vnd,
              ]),
            )
          }
        >
          <Icon name="download" size={16} />
          Xuất trang CSV
        </button>
      </header>
      <div className="toolbar">
        <label className="search-field">
          <Icon name="search" size={18} />
          <input
            placeholder="Tìm tên sản phẩm hoặc mã SKU…"
            aria-label="Tìm sản phẩm"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <select
          aria-label="Lọc danh mục"
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Tất cả danh mục</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Trạng thái sản phẩm"
          value={active}
          onChange={(e) => {
            setActive(e.target.value);
            setLow(false);
            setPage(1);
          }}
        >
          <option value="true">Đang hoạt động</option>
          <option value="false">Ngừng hoạt động</option>
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={low}
            disabled={active === "false"}
            onChange={(e) => {
              setLow(e.target.checked);
              setPage(1);
            }}
          />
          Dưới ngưỡng
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
                    <th>Sản phẩm / SKU</th>
                    <th>Danh mục</th>
                    <th className="number">Tồn kho</th>
                    <th className="number">Tối thiểu</th>
                    <th className="number">Đơn giá ước tính</th>
                    <th>Trạng thái</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong>{p.name}</strong>
                        <span className="cell-sub">{p.sku}</span>
                      </td>
                      <td className="muted">
                        {categories.find((c) => c.id === p.category_id)?.name ??
                          "Chưa phân loại"}
                      </td>
                      <td className={`number ${belowMinimum(p) ? "warning-text" : ""}`}>
                        <strong>{quantity(p.on_hand)}</strong>
                        <span className="cell-sub">{p.unit}</span>
                      </td>
                      <td className="number">{quantity(p.min_stock)}</td>
                      <td className="number nowrap">{money(p.unit_cost_vnd)}</td>
                      <td>
                        <span
                          className={`badge ${!p.is_active ? "soft" : belowMinimum(p) ? "warning" : "success"}`}
                        >
                          {!p.is_active
                            ? "Ngừng hoạt động"
                            : belowMinimum(p)
                              ? "Dưới ngưỡng"
                              : "Trong ngưỡng"}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          {user.role !== "VIEWER" && p.is_active && (
                            <button
                              className="small-button"
                              onClick={() => action({ kind: "movement", product: p })}
                            >
                              Nhập / xuất
                            </button>
                          )}
                          {user.role === "ADMIN" && (
                            <>
                              <button
                                className="small-button"
                                onClick={() => action({ kind: "product", product: p })}
                              >
                                Sửa
                              </button>
                              {p.is_active && (
                                <button
                                  className="small-button danger-text"
                                  onClick={() => action({ kind: "archive", product: p })}
                                >
                                  Ẩn
                                </button>
                              )}
                            </>
                          )}
                          {user.role === "VIEWER" && (
                            <span className="muted">Chỉ đọc</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Không có sản phẩm phù hợp"
              description="Thay đổi bộ lọc hoặc thêm sản phẩm đầu tiên để bắt đầu theo dõi kho."
            >
              {user.role === "ADMIN" && (
                <button
                  className="button primary"
                  onClick={() => action({ kind: "product" })}
                >
                  <Icon name="plus" size={16} />
                  Thêm sản phẩm
                </button>
              )}
            </Empty>
          )}
          <Pagination total={data.total} page={page} change={setPage} />
        </>
      )}
    </section>
  );
}
