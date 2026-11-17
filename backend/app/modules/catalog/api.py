from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.schemas import Page
from app.db.models import User
from app.db.session import get_session
from app.modules.auth.dependencies import admin_user, current_user
from app.modules.catalog import queries, service
from app.modules.catalog import schemas as dto
from app.modules.catalog.serializers import product_output

router = APIRouter(tags=["Catalog"], dependencies=[Depends(current_user)])


@router.get("/categories", response_model=Page[dto.CategoryRead])
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = None,
    session: Session = Depends(get_session),
):
    return queries.list_categories(session, page, page_size, active)


@router.post(
    "/categories",
    response_model=dto.CategoryRead,
    status_code=201,
    dependencies=[Depends(admin_user)],
)
def create_category(payload: dto.CategoryCreate, session: Session = Depends(get_session)):
    return service.save_category(session, payload.model_dump())


@router.patch(
    "/categories/{category_id}", response_model=dto.CategoryRead, dependencies=[Depends(admin_user)]
)
def patch_category(
    category_id: UUID, payload: dto.CategoryPatch, session: Session = Depends(get_session)
):
    return service.save_category(session, payload.model_dump(exclude_unset=True), category_id)


@router.get("/suppliers", response_model=Page[dto.SupplierRead])
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = None,
    session: Session = Depends(get_session),
):
    return queries.list_suppliers(session, page, page_size, active)


@router.post(
    "/suppliers",
    response_model=dto.SupplierRead,
    status_code=201,
    dependencies=[Depends(admin_user)],
)
def create_supplier(payload: dto.SupplierCreate, session: Session = Depends(get_session)):
    return service.save_supplier(session, payload.model_dump())


@router.patch(
    "/suppliers/{supplier_id}", response_model=dto.SupplierRead, dependencies=[Depends(admin_user)]
)
def patch_supplier(
    supplier_id: UUID, payload: dto.SupplierPatch, session: Session = Depends(get_session)
):
    return service.save_supplier(session, payload.model_dump(exclude_unset=True), supplier_id)


@router.get("/products", response_model=Page[dto.ProductRead])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    active: bool | None = None,
    category_id: UUID | None = None,
    session: Session = Depends(get_session),
):
    return queries.list_products(session, page, page_size, search, active, category_id)


@router.post(
    "/products", response_model=dto.ProductRead, status_code=201, dependencies=[Depends(admin_user)]
)
def create_product(payload: dto.ProductCreate, session: Session = Depends(get_session)):
    return service.create_product(session, payload.model_dump())


@router.get("/products/{product_id}", response_model=dto.ProductRead)
def get_product(product_id: UUID, session: Session = Depends(get_session)):
    return product_output(service.get_product(session, product_id))


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
def archive_product(
    product_id: UUID, user: User = Depends(admin_user), session: Session = Depends(get_session)
):
    return service.patch_product(session, product_id, {"is_active": False}, actor_id=user.id)
