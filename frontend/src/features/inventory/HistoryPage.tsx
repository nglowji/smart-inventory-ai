import { isMovementType, movementNames } from "./model";
import { useCallback, useState } from "react";
import type { MovementType, Range } from "../../shared/contracts";
import { useDebouncedValue } from "../../shared/hooks/useDebouncedValue";
import { useResource } from "../../shared/hooks/useResource";
import { downloadCsv } from "../../shared/lib/csv";
import { dateTime } from "../../shared/lib/format";
import { Empty, Failure, Loading } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import { Pagination } from "../../shared/ui/Pagination";
import { fetchMovements } from "./api";
import { MovementsTable } from "./MovementsTable";

export default function History({
  range,
  version,
  refresh,
}: {
  range: Range;
  version: number;
  refresh: () => void;
}) {
  const [sku, setSku] = useState("");
  const search = useDebouncedValue(sku);
  const [type, setType] = useState<MovementType | "">("");
  const [page, setPage] = useState(1);
  const load = useCallback(
    (signal: AbortSignal) =>
      fetchMovements({ ...range, sku: search, movement_type: type, page }, signal),
    [range, search, type, page],
  );
  const { data, error } = useResource(load, version);

  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>Lịch sử giao dịch</h2>
          <p>Bản ghi bất biến · Thời gian hiển thị theo giờ Việt Nam</p>
        </div>
        <button
          className="button"
          disabled={!data?.items.length}
          onClick={() =>
            data &&
            downloadCsv(
              "giao-dich-trang-hien-tai.csv",
              [
                "Thời gian (VN)",
                "SKU",
                "Loại",
                "Số lượng",
                "Đơn vị",
                "Tồn trước",
                "Tồn sau",
                "Người thực hiện",
                "Lý do",
              ],
              data.items.map((m) => [
                dateTime(m.occurred_at),
                m.sku,
                movementNames[m.movement_type],
                m.quantity,
                m.unit,
                m.stock_before,
                m.stock_after,
                m.actor_email,
                m.reason ?? "",
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
            placeholder="Lọc theo mã SKU chính xác…"
            aria-label="Lọc giao dịch theo SKU"
            value={sku}
            onChange={(e) => {
              setSku(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <select
          aria-label="Loại giao dịch"
          value={type}
          onChange={(e) => {
            const value = e.target.value;
            if (value === "" || isMovementType(value)) setType(value);
            setPage(1);
          }}
        >
          <option value="">Tất cả giao dịch</option>
          {Object.entries(movementNames).map(([key, name]) => (
            <option key={key} value={key}>
              {name}
            </option>
          ))}
        </select>
      </div>
      {error ? (
        <Failure message={error} retry={refresh} />
      ) : !data ? (
        <Loading />
      ) : (
        <>
          {data.items.length ? (
            <MovementsTable items={data.items} />
          ) : (
            <Empty
              title="Chưa có giao dịch phù hợp"
              description="Thay đổi khoảng ngày hoặc bộ lọc để xem lịch sử khác."
            />
          )}
          <Pagination page={page} total={data.total} change={setPage} />
        </>
      )}
    </section>
  );
}
