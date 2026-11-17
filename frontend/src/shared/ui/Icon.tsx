import type { ReactNode } from "react";

type Name =
  | "chat"
  | "users"
  | "audit"
  | "key"
  | "overview"
  | "box"
  | "list"
  | "truck"
  | "activity"
  | "plus"
  | "arrow"
  | "refresh"
  | "search"
  | "logout"
  | "close"
  | "menu"
  | "download"
  | "in"
  | "out"
  | "alert"
  | "check";
const paths: Record<Name, ReactNode> = {
  chat: (
    <>
      <path d="M21 11a8 8 0 0 1-8 8H8l-5 3V11a9 9 0 0 1 18 0Z" />
      <path d="M7 10h10M7 14h6" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 4v2" />
    </>
  ),
  audit: (
    <>
      <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="8" r="5" />
      <path d="m12 12 9 9M17 17l3-3M14 14l2-2" />
    </>
  ),
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  box: (
    <>
      <path d="m3 7 9-4 9 4v10l-9 4-9-4Z M3 7l9 4 9-4 M12 11v10 M7 5l9 4" />
    </>
  ),
  list: (
    <>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </>
  ),
  truck: (
    <>
      <path d="M3 6h11v11H3z M14 10h4l3 4v3h-7" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="18" cy="18" r="2" />
    </>
  ),
  activity: (
    <>
      <path d="M4 4v16h16 M8 15v-4 M13 15V7 M18 15V9" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
  refresh: (
    <>
      <path d="M20 11a8 8 0 0 0-14-5L3 9m0-5v5h5M4 13a8 8 0 0 0 14 5l3-3m0 5v-5h-5" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 5 5" />
    </>
  ),
  logout: (
    <>
      <path d="M9 4H4v16h5 M10 12h11m-4-4 4 4-4 4" />
    </>
  ),
  close: <path d="m6 6 12 12M6 18 18 6" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  download: <path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" />,
  in: (
    <>
      <path d="M12 3v12m-5-5 5 5 5-5 M4 16v5h16v-5" />
    </>
  ),
  out: (
    <>
      <path d="M12 15V3m-5 5 5-5 5 5 M4 16v5h16v-5" />
    </>
  ),
  alert: (
    <>
      <path d="m12 3 10 18H2Z M12 9v5" />
      <path d="M12 17h.01" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
};
export default function Icon({ name, size = 20 }: { name: Name; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}
