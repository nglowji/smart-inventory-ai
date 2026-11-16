import type { Product } from "../../shared/contracts";
import { useResource } from "../../shared/hooks/useResource";
import FormModal from "../../shared/ui/FormModal";
import type { OperationCallbacks } from "../operations/types";
import { fetchCategories, fetchSuppliers, saveProduct } from "./api";
import { productInput } from "./productInput";

async function loadOptions(signal: AbortSignal) {
  const [categories, suppliers] = await Promise.all([
    fetchCategories(signal),
    fetchSuppliers(signal),
  ]);
  return { categories, suppliers };
}
export default function ProductForm({
  product,
  close,
  saved,
}: OperationCallbacks & { product?: Product }) {
  const resource = useResource(loadOptions);
  const categories = resource.data?.categories ?? [];
  const suppliers = resource.data?.suppliers ?? [];
  async function submit(data: FormData) {
    await saveProduct(productInput(data, product), product?.id);
  }
  return (
    <FormModal
      title={product ? "Chỉnh sửa sản phẩm" : "Thêm sản phẩm"}
      close={close}
      saved={saved}
      submit={submit}
      ready={resource.status === "success"}
      loadError={resource.error}
    >
      <div className="form-row">
        <label>
          Mã SKU
          <input
            name="sku"
            defaultValue={product?.sku}
            required
            maxLength={64}
            autoFocus
            autoComplete="off"
            placeholder="VD: SP001"
          />
        </label>
        <label>
          Đơn vị
          <select name="unit" defaultValue={product?.unit ?? "PCS"}>
            <option value="PCS">Cái (PCS)</option>
            <option value="KG">Kilogram (KG)</option>
            <option value="LITER">Lít (LITER)</option>
          </select>
        </label>
      </div>
      <label>
        Tên sản phẩm
        <input
          name="name"
          defaultValue={product?.name}
          required
          maxLength={255}
          placeholder="Nhập tên sản phẩm"
        />
      </label>
      <div className="form-row">
        <label>
          Danh mục
          <select name="category_id" defaultValue={product?.category_id ?? ""}>
            <option value="">Chưa phân loại</option>
            {categories
              .filter((c) => c.is_active || c.id === product?.category_id)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {!c.is_active ? " (ngừng hoạt động)" : ""}
                </option>
              ))}
          </select>
        </label>
        <label>
          Nhà cung cấp mặc định
          <select
            name="default_supplier_id"
            defaultValue={product?.default_supplier_id ?? ""}
          >
            <option value="">Chưa chọn</option>
            {suppliers
              .filter((s) => s.is_active || s.id === product?.default_supplier_id)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {!s.is_active ? " (ngừng hoạt động)" : ""}
                </option>
              ))}
          </select>
        </label>
      </div>
      <div className="form-row">
        <label>
          Tồn tối thiểu
          <input
            name="min_stock"
            type="number"
            min="0"
            step="0.001"
            defaultValue={product?.min_stock ?? "0"}
            required
          />
        </label>
        <label>
          Thời gian chờ nhập (ngày)
          <input
            name="lead_time_days"
            type="number"
            min="0"
            step="1"
            defaultValue={product?.lead_time_days ?? 7}
            required
          />
        </label>
      </div>
      <label>
        Đơn giá ước tính (VND)
        <input
          name="unit_cost_vnd"
          type="number"
          min="0"
          step="0.01"
          defaultValue={product?.unit_cost_vnd ?? "0"}
          required
        />
      </label>
      <p className="form-help">
        Sản phẩm mới có tồn bằng 0. Thay đổi số lượng qua giao dịch nhập/xuất; không sửa
        tồn trực tiếp.
      </p>
    </FormModal>
  );
}
