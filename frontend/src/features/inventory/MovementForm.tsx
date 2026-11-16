import { useRef, useState } from "react";
import type { MovementType, Product, User } from "../../shared/contracts";
import { useResource } from "../../shared/hooks/useResource";
import { quantity } from "../../shared/lib/format";
import { formText, optionalFormText } from "../../shared/lib/forms";
import FormModal from "../../shared/ui/FormModal";
import { fetchActiveProducts, fetchSuppliers } from "../catalog/api";
import type { OperationCallbacks } from "../operations/types";
import type { MovementInput } from "./api";
import { createMovement } from "./api";
import { isMovementType } from "./model";

async function loadOptions(signal: AbortSignal) {
  const [products, suppliers] = await Promise.all([
    fetchActiveProducts(signal),
    fetchSuppliers(signal),
  ]);
  return { products, suppliers };
}
export default function MovementForm({
  product,
  type = "IN",
  user,
  close,
  saved,
}: OperationCallbacks & {
  product?: Product;
  type?: MovementType;
  user: User;
}) {
  const resource = useResource(loadOptions);
  const products = resource.data?.products ?? [];
  const suppliers = resource.data?.suppliers ?? [];
  const [productId, setProductId] = useState(product?.id ?? "");
  const [movementType, setMovementType] = useState<MovementType>(type);
  const retry = useRef<{ body: string; key: string } | null>(null);
  const current = products.find((item) => item.id === productId);
  async function submit(data: FormData) {
    const payload: MovementInput = {
      product_id: productId,
      movement_type: movementType,
      quantity: formText(data, "quantity"),
      reason: optionalFormText(data, "reason"),
      reference_code: optionalFormText(data, "reference_code"),
      supplier_id: movementType === "IN" ? optionalFormText(data, "supplier_id") : null,
    };
    const body = JSON.stringify(payload);
    if (retry.current?.body !== body) retry.current = { body, key: crypto.randomUUID() };
    await createMovement(payload, retry.current.key);
  }
  return (
    <FormModal
      title="Tạo giao dịch kho"
      submitLabel="Ghi giao dịch"
      successMessage="Đã ghi giao dịch. Tồn kho và dashboard được cập nhật."
      close={close}
      saved={saved}
      submit={submit}
      ready={resource.status === "success"}
      loadError={resource.error}
    >
      <label>
        Sản phẩm
        <select
          required
          value={productId}
          onChange={(event) => setProductId(event.target.value)}
        >
          <option value="">Chọn sản phẩm</option>
          {products.map((p) => (
            <option value={p.id} key={p.id}>
              {p.sku} — {p.name}
            </option>
          ))}
        </select>
      </label>
      {current && (
        <div className="balance-preview">
          <span>Tồn hiện tại</span>
          <strong>
            {quantity(current.on_hand)} {current.unit}
          </strong>
        </div>
      )}
      <div className="form-row">
        <label>
          Loại giao dịch
          <select
            value={movementType}
            onChange={(event) =>
              isMovementType(event.target.value) && setMovementType(event.target.value)
            }
          >
            <option value="IN">Nhập kho</option>
            <option value="OUT">Xuất kho</option>
            {user.role === "ADMIN" && (
              <>
                <option value="ADJUST_IN">Điều chỉnh tăng</option>
                <option value="ADJUST_OUT">Điều chỉnh giảm</option>
              </>
            )}
          </select>
        </label>
        <label>
          Số lượng {current ? `(${current.unit})` : ""}
          <input
            name="quantity"
            type="number"
            required
            min={current?.unit === "PCS" ? "1" : "0.001"}
            step={current?.unit === "PCS" ? "1" : "0.001"}
            placeholder="0"
          />
        </label>
      </div>
      {movementType === "IN" && (
        <label>
          Nhà cung cấp
          <select name="supplier_id" defaultValue="">
            <option value="">Không chọn</option>
            {suppliers
              .filter((s) => s.is_active)
              .map((s) => (
                <option value={s.id} key={s.id}>
                  {s.name}
                </option>
              ))}
          </select>
        </label>
      )}
      <label>
        Lý do {movementType !== "IN" ? "(bắt buộc)" : "(tùy chọn)"}
        <textarea
          name="reason"
          required={movementType !== "IN"}
          minLength={movementType.startsWith("ADJUST") ? 10 : undefined}
          maxLength={2000}
          rows={3}
          placeholder={
            movementType.startsWith("ADJUST")
              ? "Mô tả chênh lệch kiểm kê, tối thiểu 10 ký tự"
              : "Ghi chú cho giao dịch này"
          }
        />
      </label>
      <label>
        Mã tham chiếu
        <input
          name="reference_code"
          maxLength={50}
          placeholder="VD: NK-001 (không bắt buộc)"
        />
      </label>
      <p className="form-help">
        Giao dịch đã ghi không thể sửa hoặc xóa. Hệ thống kiểm tra tồn và chống ghi trùng
        khi gửi lại.
      </p>
    </FormModal>
  );
}
