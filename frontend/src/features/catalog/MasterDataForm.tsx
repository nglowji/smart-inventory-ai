import { formText, optionalFormText } from "../../shared/lib/forms";
import FormModal from "../../shared/ui/FormModal";
import type { Action, OperationCallbacks } from "../operations/types";
import { saveCategory, saveSupplier } from "./api";

type MasterAction = Extract<Action, { kind: "category" | "supplier" }>;
export default function MasterDataForm({
  action,
  close,
  saved,
}: OperationCallbacks & { action: MasterAction }) {
  const name = action.kind === "category" ? "danh mục" : "nhà cung cấp";
  const title = `${action.item ? "Sửa" : "Thêm"} ${name}`;
  async function submit(data: FormData) {
    if (action.kind === "category")
      await saveCategory(formText(data, "name"), action.item?.id);
    else
      await saveSupplier(
        {
          name: formText(data, "name"),
          phone: optionalFormText(data, "phone"),
          email: optionalFormText(data, "email"),
        },
        action.item?.id,
      );
  }
  return (
    <FormModal title={title} close={close} saved={saved} submit={submit}>
      <label>
        Tên {action.kind === "category" ? "danh mục" : "nhà cung cấp"}
        <input
          name="name"
          defaultValue={action.item?.name}
          required
          maxLength={action.kind === "category" ? 120 : 200}
          autoFocus
        />
      </label>
      {action.kind === "supplier" && (
        <>
          <label>
            Số điện thoại
            <input
              name="phone"
              defaultValue={action.item?.phone ?? ""}
              type="tel"
              maxLength={30}
            />
          </label>
          <label>
            Email
            <input
              name="email"
              type="email"
              defaultValue={action.item?.email ?? ""}
              maxLength={255}
            />
          </label>
        </>
      )}
    </FormModal>
  );
}
