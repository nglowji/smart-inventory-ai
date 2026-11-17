import { useCallback, useState } from "react";
import type { AuditEvent, Range } from "../../shared/contracts";
import { useResource } from "../../shared/hooks/useResource";
import { dateTime } from "../../shared/lib/format";
import { isRole, roleLabels } from "../../shared/lib/roles";
import { Empty, Failure, Loading } from "../../shared/ui/Feedback";
import { Pagination } from "../../shared/ui/Pagination";
import { fetchAudit } from "./api";
import { auditLabels, detailLabels, isAuditEvent } from "./model";

function displayValue(value: string | boolean): string {
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (isRole(value)) return roleLabels[value];
  return value === "invalid_credentials" ? "Thông tin đăng nhập không đúng" : value;
}

export default function AuditPage({
  range,
  version,
  refresh,
}: {
  range: Range;
  version: number;
  refresh: () => void;
}) {
  const [event, setEvent] = useState<AuditEvent | "">("");
  const [page, setPage] = useState(1);
  const load = useCallback(
    (signal: AbortSignal) => fetchAudit(range, page, event, signal),
    [range, page, event],
  );
  const { data, error } = useResource(load, version);
  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>Nhật ký kiểm toán</h2>
          <p>Chỉ Admin được đọc · Ghi nhận người thực hiện, thời gian và request ID</p>
        </div>
      </header>
      <div className="toolbar">
        <select
          aria-label="Lọc loại sự kiện"
          value={event}
          onChange={(e) => {
            const next = e.target.value;
            if (next === "" || isAuditEvent(next)) {
              setEvent(next);
              setPage(1);
            }
          }}
        >
          <option value="">Tất cả sự kiện</option>
          {Object.entries(auditLabels).map(([value, label]) => (
            <option value={value} key={value}>
              {label}
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
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Thời gian</th>
                    <th>Sự kiện</th>
                    <th>Người thực hiện</th>
                    <th>Chi tiết</th>
                    <th>Request ID</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((entry) => (
                    <tr key={entry.id}>
                      <td className="nowrap muted">{dateTime(entry.created_at)}</td>
                      <td>
                        <strong>{auditLabels[entry.event_type]}</strong>
                        <span className="cell-sub" title={entry.target_id ?? undefined}>
                          {entry.target_type}
                          {entry.target_id ? ` · ${entry.target_id.slice(0, 8)}` : ""}
                        </span>
                      </td>
                      <td>{entry.actor_email ?? "Chưa xác thực"}</td>
                      <td>
                        <div className="audit-details">
                          {Object.entries(entry.details).map(([key, value]) => (
                            <span key={key}>
                              {detailLabels[key] ?? key}: {displayValue(value)}
                            </span>
                          ))}
                          {!Object.keys(entry.details).length && (
                            <span className="muted">—</span>
                          )}
                        </div>
                      </td>
                      <td>
                        <code
                          className="request-reference"
                          title={entry.request_id ?? undefined}
                        >
                          {entry.request_id?.slice(0, 8) ?? "—"}
                        </code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Chưa có sự kiện phù hợp"
              description="Thay đổi khoảng ngày hoặc loại sự kiện để tra cứu nhật ký."
            />
          )}
          <Pagination page={page} total={data.total} change={setPage} />
        </>
      )}
    </section>
  );
}
