import type { ManagedUser, Role } from "../../shared/contracts";
import { formText } from "../../shared/lib/forms";
import { isRole, roleLabels } from "../../shared/lib/roles";
import FormModal from "../../shared/ui/FormModal";
import type { OperationCallbacks } from "../operations/types";
import { createUser, updateUser } from "./api";
import type { UserPatchInput } from "./api";

export default function UserForm({
  account,
  close,
  saved,
}: OperationCallbacks & { account?: ManagedUser }) {
  async function submit(data: FormData) {
    const role = formText(data, "role");
    if (!isRole(role)) throw new Error("Vai trò không hợp lệ.");
    const password = String(data.get("password") ?? "");
    if (!account) {
      await createUser({ email: formText(data, "email"), role, password });
      return;
    }
    const payload: UserPatchInput = {};
    if (role !== account.role) payload.role = role;
    const active = data.get("is_active") === "on";
    if (active !== account.is_active) payload.is_active = active;
    if (password) payload.password = password;
    await updateUser(account.id, payload);
  }
  return (
    <FormModal
      title={account ? "Quản lý tài khoản" : "Thêm tài khoản"}
      close={close}
      saved={saved}
      submit={submit}
    >
      <label>
        Email
        <input
          name="email"
          type="email"
          required
          maxLength={255}
          defaultValue={account?.email}
          readOnly={Boolean(account)}
          autoComplete="off"
          autoFocus
        />
      </label>
      <label>
        Vai trò
        <select name="role" defaultValue={account?.role ?? "VIEWER"}>
          {(Object.keys(roleLabels) as Role[]).map((role) => (
            <option value={role} key={role}>
              {roleLabels[role]}
            </option>
          ))}
        </select>
      </label>
      <label>
        {account ? "Đặt lại mật khẩu (tùy chọn)" : "Mật khẩu ban đầu"}
        <input
          name="password"
          type="password"
          required={!account}
          minLength={12}
          maxLength={128}
          autoComplete="new-password"
          placeholder={account ? "Để trống để giữ nguyên" : "Từ 12 đến 128 ký tự"}
        />
      </label>
      {account && (
        <label className="account-active">
          <input type="checkbox" name="is_active" defaultChecked={account.is_active} />
          Tài khoản đang hoạt động
        </label>
      )}
      <p className="form-help">
        Thay đổi quyền, khóa hoặc đặt lại mật khẩu sẽ thu hồi các phiên đang đăng nhập. Hệ
        thống luôn giữ ít nhất một Admin hoạt động.
      </p>
    </FormModal>
  );
}
