import type { Category, MovementType, Product, Supplier } from "../../shared/contracts";

export type Action =
  | { kind: "product"; product?: Product }
  | { kind: "archive"; product: Product }
  | { kind: "movement"; product?: Product; type?: MovementType }
  | { kind: "category"; item?: Category }
  | { kind: "supplier"; item?: Supplier };

export type OperationCallbacks = { close: () => void; saved: (message: string) => void };
