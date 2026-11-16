from pathlib import Path

root = Path(__file__).resolve().parents[1] / "frontend" / "src"
source = (root / "features/operations/OperationDialog.tsx").read_text(encoding="utf-8")


def write(path, code):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8")


product = source[source.index('              <div className="form-row">'):source.index('          ) : action.kind === "movement" ?')]
product = product[:product.rindex("</>")]
write("features/catalog/ProductForm.tsx", '''import type { Product } from "../../shared/contracts";
import type { OperationCallbacks } from "../operations/types";
import FormModal from "../../shared/ui/FormModal";
import { useResource } from "../../shared/hooks/useResource";
import { fetchCategories, fetchSuppliers, saveProduct } from "./api";
import { productInput } from "./productInput";

async function loadOptions(signal: AbortSignal) {
  const [categories, suppliers] = await Promise.all([fetchCategories(signal), fetchSuppliers(signal)]);
  return { categories, suppliers };
}
export default function ProductForm({ product, close, saved }: OperationCallbacks & { product?: Product }) {
  const resource = useResource(loadOptions);
  const categories = resource.data?.categories ?? [];
  const suppliers = resource.data?.suppliers ?? [];
  async function submit(data: FormData) { await saveProduct(productInput(data, product), product?.id); }
  return <FormModal title={product ? "Chỉnh sửa sản phẩm" : "Thêm sản phẩm"} close={close} saved={saved} submit={submit} ready={resource.status === "success"} loadError={resource.error}>
''' + product + "</FormModal>;\n}\n")

start = source.index('          ) : action.kind === "movement" ?')
movement = source[source.index('              <label>', start):source.index('          ) : (', start)]
movement = movement[:movement.rindex("</>")]
movement = movement.replace("setMovementType(event.target.value)", "isMovementType(event.target.value) && setMovementType(event.target.value)")
write("features/inventory/MovementForm.tsx", '''import { useRef, useState } from "react";
import type { MovementType, Product, User } from "../../shared/contracts";
import type { OperationCallbacks } from "../operations/types";
import FormModal from "../../shared/ui/FormModal";
import { useResource } from "../../shared/hooks/useResource";
import { fetchActiveProducts, fetchSuppliers } from "../catalog/api";
import { quantity } from "../../shared/lib/format";
import { formText, optionalFormText } from "../../shared/lib/forms";
import { createMovement } from "./api";
import type { MovementInput } from "./api";
import { isMovementType } from "./model";

async function loadOptions(signal: AbortSignal) {
  const [products, suppliers] = await Promise.all([fetchActiveProducts(signal), fetchSuppliers(signal)]);
  return { products, suppliers };
}
export default function MovementForm({ product, type = "IN", user, close, saved }: OperationCallbacks & {
  product?: Product; type?: MovementType; user: User;
}) {
  const resource = useResource(loadOptions);
  const products = resource.data?.products ?? [];
  const suppliers = resource.data?.suppliers ?? [];
  const [productId, setProductId] = useState(product?.id ?? "");
  const [movementType, setMovementType] = useState<MovementType>(type);
  const retry = useRef<{ body: string; key: string } | null>(null);
  const current = products.find(item => item.id === productId);
  async function submit(data: FormData) {
    const payload: MovementInput = {
      product_id: productId, movement_type: movementType, quantity: formText(data, "quantity"),
      reason: optionalFormText(data, "reason"), reference_code: optionalFormText(data, "reference_code"),
      supplier_id: movementType === "IN" ? optionalFormText(data, "supplier_id") : null,
    };
    const body = JSON.stringify(payload);
    if (retry.current?.body !== body) retry.current = { body, key: crypto.randomUUID() };
    await createMovement(payload, retry.current.key);
  }
  return <FormModal title="Tạo giao dịch kho" submitLabel="Ghi giao dịch" successMessage="Đã ghi giao dịch. Tồn kho và dashboard được cập nhật." close={close} saved={saved} submit={submit} ready={resource.status === "success"} loadError={resource.error}>
''' + movement + "</FormModal>;\n}\n")

start = source.index('          ) : (', start)
master = source[source.index('              <label>', start):source.index('        </fieldset>', start)]
master = master[:master.rindex("</>")]
write("features/catalog/MasterDataForm.tsx", '''import FormModal from "../../shared/ui/FormModal";
import { formText, optionalFormText } from "../../shared/lib/forms";
import type { Action, OperationCallbacks } from "../operations/types";
import { saveCategory, saveSupplier } from "./api";

type MasterAction = Extract<Action, { kind: "category" | "supplier" }>;
export default function MasterDataForm({ action, close, saved }: OperationCallbacks & { action: MasterAction }) {
  const name = action.kind === "category" ? "danh mục" : "nhà cung cấp";
  const title = `${action.item ? "Sửa" : "Thêm"} ${name}`;
  async function submit(data: FormData) {
    if (action.kind === "category") await saveCategory(formText(data, "name"), action.item?.id);
    else await saveSupplier({ name: formText(data, "name"), phone: optionalFormText(data, "phone"), email: optionalFormText(data, "email") }, action.item?.id);
  }
  return <FormModal title={title} close={close} saved={saved} submit={submit}>
''' + master + "</FormModal>;\n}\n")

start = source.index('            <div className="archive-note">')
end = source.index('          ) : action.kind === "product"', start)
archive = source[start:end].replace("action.product", "product")
write("features/catalog/ArchiveProductForm.tsx", '''import type { Product } from "../../shared/contracts";
import type { OperationCallbacks } from "../operations/types";
import FormModal from "../../shared/ui/FormModal";
import { archiveProduct } from "./api";

export default function ArchiveProductForm({ product, close, saved }: OperationCallbacks & { product: Product }) {
  async function submit() { await archiveProduct(product.id); }
  return <FormModal title="Ngừng hoạt động sản phẩm" submitLabel="Ngừng hoạt động" danger close={close} saved={saved} submit={submit}>
''' + archive + "</FormModal>;\n}\n")

write("features/operations/OperationDialog.tsx", '''import type { User } from "../../shared/contracts";
import type { Action, OperationCallbacks } from "./types";
import ProductForm from "../catalog/ProductForm";
import ArchiveProductForm from "../catalog/ArchiveProductForm";
import MasterDataForm from "../catalog/MasterDataForm";
import MovementForm from "../inventory/MovementForm";

export default function OperationDialog({ action, user, close, saved }: OperationCallbacks & { action: Action; user: User }) {
  const callbacks = { close, saved };
  switch (action.kind) {
    case "product": return <ProductForm product={action.product} {...callbacks} />;
    case "archive": return <ArchiveProductForm product={action.product} {...callbacks} />;
    case "movement": return <MovementForm product={action.product} type={action.type} user={user} {...callbacks} />;
    case "category":
    case "supplier": return <MasterDataForm action={action} {...callbacks} />;
  }
}
''')
