import type { User } from "../../shared/contracts";
import ArchiveProductForm from "../catalog/ArchiveProductForm";
import MasterDataForm from "../catalog/MasterDataForm";
import ProductForm from "../catalog/ProductForm";
import MovementForm from "../inventory/MovementForm";
import type { Action, OperationCallbacks } from "./types";

export default function OperationDialog({
  action,
  user,
  close,
  saved,
}: OperationCallbacks & { action: Action; user: User }) {
  const callbacks = { close, saved };
  switch (action.kind) {
    case "product":
      return <ProductForm product={action.product} {...callbacks} />;
    case "archive":
      return <ArchiveProductForm product={action.product} {...callbacks} />;
    case "movement":
      return (
        <MovementForm
          product={action.product}
          type={action.type}
          user={user}
          {...callbacks}
        />
      );
    case "category":
    case "supplier":
      return <MasterDataForm action={action} {...callbacks} />;
  }
}
