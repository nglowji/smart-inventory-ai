export function Pagination({
  total,
  page,
  pageSize = 10,
  change,
}: {
  total: number;
  page: number;
  pageSize?: number;
  change: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="table-footer">
      <span>
        {total
          ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} / ${total} bản ghi`
          : "0 bản ghi"}
      </span>
      <div className="pagination">
        <button
          disabled={page <= 1}
          onClick={() => change(page - 1)}
          aria-label="Trang trước"
        >
          ‹
        </button>
        <span>
          Trang {page} / {pages}
        </span>
        <button
          disabled={page >= pages}
          onClick={() => change(page + 1)}
          aria-label="Trang sau"
        >
          ›
        </button>
      </div>
    </div>
  );
}
