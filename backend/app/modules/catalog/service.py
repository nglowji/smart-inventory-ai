from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError
from app.db.models import Category, Product, StockBalance, StockMovement, Supplier
from app.modules.catalog.schemas import ProductRead


def commit_catalog(session: Session):
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
        if constraint == "uq_products_sku":
            raise DomainError(409, "SKU_ALREADY_EXISTS", "SKU đã tồn tại.") from None
        if constraint == "uq_categories_name":
            raise DomainError(409, "CATEGORY_ALREADY_EXISTS", "Tên danh mục đã tồn tại.") from None
        raise


def paginate(session: Session, statement, page: int, page_size: int):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    items = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def require_record(session: Session, model, record_id: UUID):
    record = session.get(model, record_id)
    if record is None:
        raise DomainError(404, "NOT_FOUND", "Không tìm thấy dữ liệu.")
    return record


def validate_references(session: Session, data: dict):
    for field, model in (("category_id", Category), ("default_supplier_id", Supplier)):
        if data.get(field) is not None:
            ref = session.get(model, data[field])
            if ref is None or not ref.is_active:
                raise DomainError(422, "VALIDATION_ERROR", "Danh mục/nhà cung cấp không khả dụng.")


def get_product(session: Session, product_id: UUID, *, lock: bool = False) -> Product:
    statement = select(Product).where(Product.id == product_id)
    if lock:
        statement = statement.with_for_update()
    else:
        statement = statement.options(joinedload(Product.balance))
    product = session.scalar(statement)
    if product is None:
        raise DomainError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
    return product


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


def create_product(session: Session, data: dict):
    validate_references(session, data)
    product = Product(**data)
    product.balance = StockBalance(on_hand=0)
    session.add(product)
    # Relationship orders both INSERTs; one commit, so a balance failure rolls back product too.
    commit_catalog(session)
    session.refresh(product)
    return product_output(product)


def patch_product(session: Session, product_id: UUID, data: dict):
    product = get_product(session, product_id, lock=True)
    validate_references(session, data)
    if "unit" in data and data["unit"] != product.unit:
        has_history = session.scalar(select(exists().where(StockMovement.product_id == product_id)))
        if has_history:
            raise DomainError(409, "UNIT_IMMUTABLE", "Không đổi đơn vị khi đã có giao dịch kho.")
    for key, value in data.items():
        setattr(product, key, value)
    commit_catalog(session)
    session.refresh(product)
    return product_output(product)
