import Icon from "../../shared/ui/Icon";
export default function Topbar({
  label,
  role,
  mobile,
  toggleMenu,
}: {
  label: string;
  role: string;
  mobile: boolean;
  toggleMenu: () => void;
}) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <button
          className="icon-button mobile-toggle"
          onClick={toggleMenu}
          aria-label="Mở menu"
          aria-expanded={mobile}
        >
          <Icon name="menu" />
        </button>
        <span>Kho chính</span>
        <span className="crumb-divider">/</span>
        <strong>{label}</strong>
      </div>
      <div className="topbar-right">
        <span className="topbar-caption">Giờ Việt Nam · VND</span>
        <span className="badge soft">{role}</span>
      </div>
    </header>
  );
}
