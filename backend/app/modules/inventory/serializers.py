from app.db.models import Product, StockMovement


def movement_output(movement: StockMovement, product: Product, actor_email: str | None = None):
    return {
        "id": str(movement.id),
        "product_id": str(movement.product_id),
        "sku": product.sku,
        "name": product.name,
        "unit": product.unit,
        "movement_type": movement.movement_type,
        "quantity": f"{movement.quantity:.3f}",
        "stock_before": f"{movement.stock_before:.3f}",
        "stock_after": f"{movement.stock_after:.3f}",
        "reason": movement.reason,
        "supplier_id": str(movement.supplier_id) if movement.supplier_id else None,
        "reference_code": movement.reference_code,
        "actor_id": str(movement.actor_id),
        "actor_email": actor_email,
        "occurred_at": movement.occurred_at,
    }
