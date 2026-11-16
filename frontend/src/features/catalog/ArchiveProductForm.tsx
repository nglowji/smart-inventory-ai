import type { Product } from "../../shared/contracts";
import FormModal from "../../shared/ui/FormModal";
import type { OperationCallbacks } from "../operations/types";
import { archiveProduct } from "./api";

export default function ArchiveProductForm({
  product,
  close,
  saved,
}: OperationCallbacks & { product: Product }) {
  async function submit() {
    await archiveProduct(product.id);
  }
  return (
    <FormModal
      title="Ngừng hoạt động sản phẩm"
      submitLabel="Ngừng hoạt động"
      danger
      close={close}
      saved={saved}
      submit={submit}
    >
      <div className="archive-note">
        <p>
          Bạn muốn ngừng hoạt động{" "}
          <strong>
            {product.sku} — {product.name}
          </strong>
          ?
        </p>
        <p>
          Sản phẩm sẽ không thể nhập/xuất thêm. Tồn hiện tại và lịch sử vẫn được giữ lại.
        </p>
      </div>
    </FormModal>
  );
}
