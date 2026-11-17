import type { ReactNode } from "react";

export default function ChartDataTable({
  title,
  headers,
  rows,
}: {
  title: string;
  headers: string[];
  rows: { key: string; cells: ReactNode[] }[];
}) {
  return (
    <details className="chart-data">
      <summary>Xem dữ liệu biểu đồ</summary>
      <div className="table-scroll">
        <table>
          <caption className="sr-only">{title}</caption>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                {row.cells.map((cell, index) => (
                  <td key={index}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
