import { useEffect } from "react";
import LoginPage from "../features/auth/LoginPage";
import { useAuth } from "../features/auth/useAuth";
import { Loading } from "../shared/ui/Feedback";
import Workspace from "./Workspace";

export default function App() {
  const auth = useAuth();
  useEffect(() => {
    if (!auth.user) document.title = "SmartInventory — Đăng nhập";
  }, [auth.user]);
  if (auth.loading)
    return (
      <div className="boot-screen">
        <Loading />
      </div>
    );
  if (!auth.user) return <LoginPage login={auth.login} message={auth.message} />;
  return <Workspace key={auth.user.id} user={auth.user} logout={auth.logout} />;
}
