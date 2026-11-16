from app.db.models import Product
from app.modules.catalog.schemas import ProductRead


def product_output(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        default_supplier_id=product.default_supplier_id,
        unit=product.unit,
        min_stock=f"{product.min_stock:.3f}",
        lead_time_days=product.lead_time_days,
        unit_cost_vnd=f"{product.unit_cost_vnd:.2f}",
        on_hand=f"{product.balance.on_hand:.3f}",
        is_active=product.is_active,
    )
