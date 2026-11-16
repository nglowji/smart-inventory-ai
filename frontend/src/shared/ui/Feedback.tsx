import type { ReactNode } from "react";
import Icon from "./Icon";
export function Empty({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="box" size={28} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading-state" role="status">
      <span className="spinner" />
      Đang tải dữ liệu mới nhất…
    </div>
  );
}
export function Failure({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <Icon name="alert" />
      <h3>Chưa tải được dữ liệu</h3>
      <p>{message}</p>
      <button className="button" onClick={retry}>
        Thử lại
      </button>
    </div>
  );
}
