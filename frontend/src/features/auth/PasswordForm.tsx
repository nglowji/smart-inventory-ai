import { expireSession, getToken } from "../../shared/api/session";
import FormModal from "../../shared/ui/FormModal";
import type { OperationCallbacks } from "../operations/types";
import { changePassword } from "./api";

export default function PasswordForm({ close, saved }: OperationCallbacks) {
  async function submit(data: FormData) {
    const current = String(data.get("current_password") ?? "");
    const next = String(data.get("new_password") ?? "");
    if (next !== String(data.get("confirmation") ?? ""))
      throw new Error("Mật khẩu xác nhận không khớp.");
    const token = getToken();
    const result = await changePassword({
      current_password: current,
      new_password: next,
    });
    expireSession(token, result.message);
  }
  return (
    <FormModal
      title="Đổi mật khẩu cá nhân"
      submitLabel="Đổi mật khẩu"
      close={close}
      saved={saved}
      submit={submit}
    >
      <label>
        Mật khẩu hiện tại
        <input
          name="current_password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={1024}
          autoFocus
        />
      </label>
      <label>
        Mật khẩu mới
        <input
          name="new_password"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
        />
      </label>
      <label>
        Nhập lại mật khẩu mới
        <input
          name="confirmation"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
        />
      </label>
      <p className="form-help">
        Dùng từ 12 đến 128 ký tự. Đổi mật khẩu sẽ kết thúc mọi phiên của tài khoản; bạn
        cần đăng nhập lại.
      </p>
    </FormModal>
  );
}
