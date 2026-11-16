from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Category, Product, Supplier
from app.db.session import get_session
from app.modules.auth.api import admin_user, current_user
from app.modules.catalog import schemas as dto
from app.modules.catalog import service

router = APIRouter(tags=["Catalog"], dependencies=[Depends(current_user)])


@router.get("/categories", response_model=dto.Page[dto.CategoryRead])
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = None,
    session: Session = Depends(get_session),
):
    statement = select(Category).order_by(Category.name, Category.id)
    if active is not None:
        statement = statement.where(Category.is_active == active)
    return service.paginate(session, statement, page, page_size)


@router.post(
    "/categories",
    response_model=dto.CategoryRead,
    status_code=201,
    dependencies=[Depends(admin_user)],
)
def create_category(payload: dto.CategoryCreate, session: Session = Depends(get_session)):
    category = Category(**payload.model_dump())
    session.add(category)
    service.commit_catalog(session)
    return category


@router.patch(
    "/categories/{category_id}", response_model=dto.CategoryRead, dependencies=[Depends(admin_user)]
)
def patch_category(
    category_id: UUID, payload: dto.CategoryPatch, session: Session = Depends(get_session)
):
    category = service.require_record(session, Category, category_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    service.commit_catalog(session)
    return category


@router.get("/suppliers", response_model=dto.Page[dto.SupplierRead])
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = None,
    session: Session = Depends(get_session),
):
    statement = select(Supplier).order_by(Supplier.name, Supplier.id)
    if active is not None:
        statement = statement.where(Supplier.is_active == active)
    return service.paginate(session, statement, page, page_size)


@router.post(
    "/suppliers",
    response_model=dto.SupplierRead,
    status_code=201,
    dependencies=[Depends(admin_user)],
)
def create_supplier(payload: dto.SupplierCreate, session: Session = Depends(get_session)):
    supplier = Supplier(**payload.model_dump())
    session.add(supplier)
    service.commit_catalog(session)
    return supplier


@router.patch(
    "/suppliers/{supplier_id}", response_model=dto.SupplierRead, dependencies=[Depends(admin_user)]
)
def patch_supplier(
    supplier_id: UUID, payload: dto.SupplierPatch, session: Session = Depends(get_session)
):
    supplier = service.require_record(session, Supplier, supplier_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    service.commit_catalog(session)
    return supplier


@router.get("/products", response_model=dto.Page[dto.ProductRead])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    active: bool | None = None,
    category_id: UUID | None = None,
    session: Session = Depends(get_session),
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
    result = service.paginate(session, statement, page, page_size)
    result["items"] = [service.product_output(product) for product in result["items"]]
    return result


@router.post(
    "/products", response_model=dto.ProductRead, status_code=201, dependencies=[Depends(admin_user)]
)
def create_product(payload: dto.ProductCreate, session: Session = Depends(get_session)):
    return service.create_product(session, payload.model_dump())


@router.get("/products/{product_id}", response_model=dto.ProductRead)
def get_product(product_id: UUID, session: Session = Depends(get_session)):
    return service.product_output(service.get_product(session, product_id))


@router.patch(
    "/products/{product_id}", response_model=dto.ProductRead, dependencies=[Depends(admin_user)]
)
def patch_product(
    product_id: UUID, payload: dto.ProductPatch, session: Session = Depends(get_session)
):
    return service.patch_product(session, product_id, payload.model_dump(exclude_unset=True))


@router.post(
    "/products/{product_id}/archive",
    response_model=dto.ProductRead,
    dependencies=[Depends(admin_user)],
)
def archive_product(product_id: UUID, session: Session = Depends(get_session)):
    return service.patch_product(session, product_id, {"is_active": False})
