from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Category, Product, Supplier
from app.db.pagination import paginate
from app.modules.catalog.serializers import product_output


def list_categories(session: Session, page: int, page_size: int, active: bool | None):
    statement = select(Category).order_by(Category.name, Category.id)
    if active is not None:
        statement = statement.where(Category.is_active == active)
    return paginate(session, statement, page, page_size)


def list_suppliers(session: Session, page: int, page_size: int, active: bool | None):
    statement = select(Supplier).order_by(Supplier.name, Supplier.id)
    if active is not None:
        statement = statement.where(Supplier.is_active == active)
    return paginate(session, statement, page, page_size)


def list_products(
    session: Session,
    page: int,
    page_size: int,
    search: str | None,
    active: bool | None,
    category_id: UUID | None,
):
    statement = (
        select(Product).options(joinedload(Product.balance)).order_by(Product.sku, Product.id)
    )
    if search:
        statement = statement.where(
            Product.sku.icontains(search.strip(), autoescape=True)
            | Product.name.icontains(search.strip(), autoescape=True)
        )
    if active is not None:
        statement = statement.where(Product.is_active == active)
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    result = paginate(session, statement, page, page_size)
    result["items"] = [product_output(product) for product in result["items"]]
    return result
