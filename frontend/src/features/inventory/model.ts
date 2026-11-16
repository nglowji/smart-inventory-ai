import type { MovementType } from "../../shared/contracts";

export const movementNames: Record<MovementType, string> = {
  IN: "Nhập kho",
  OUT: "Xuất kho",
  ADJUST_IN: "Điều chỉnh tăng",
  ADJUST_OUT: "Điều chỉnh giảm",
};
export function isMovementType(value: string): value is MovementType {
  return Object.hasOwn(movementNames, value);
}
