import type { Action } from "../../features/operations/types";
import Icon from "../../shared/ui/Icon";
export default function PageHeader({
  title,
  description,
  primaryAction,
  actionLabel,
  refresh,
  setAction,
}: {
  title: string;
  description: string;
  primaryAction: Action | null;
  actionLabel: string;
  refresh: () => void;
  setAction: (action: Action) => void;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="page-kicker">KHÔNG GIAN LÀM VIỆC</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      <div className="heading-actions">
        <button className="button" onClick={refresh}>
          <Icon name="refresh" size={16} />
          Làm mới
        </button>
        {primaryAction && (
          <button className="button primary" onClick={() => setAction(primaryAction)}>
            <Icon name="plus" size={17} />
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}
