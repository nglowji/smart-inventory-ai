"""Run manually with --apply; demo inventory is atomic, labeled and repeat-safe."""

import argparse
import json
import os
from datetime import UTC, datetime, timedelta

from dotenv import dotenv_values
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, Settings
from app.core.errors import DomainError
from app.db.connection import build_engine
from app.db.models import AuditLog, Category, Product, StockBalance, StockMovement, Supplier, User
from app.demo.dataset import CATEGORIES, DATASET_ID, PRODUCTS, SUPPLIERS, VERSION, entity_id
from app.demo.planning import plan_product, preview
from app.modules.audit.service import record_event
from app.modules.catalog.schemas import ProductCreate
from app.modules.inventory.idempotency import request_fingerprint
from app.modules.inventory.policies import require_movement_permission
from app.modules.inventory.schemas import MovementCreate


def import_demo(session: Session, admin_email: str, *, now: datetime | None = None) -> dict:
    anchor = (now or datetime.now(UTC)) - timedelta(hours=4)
    report = {"categories": len(CATEGORIES), "suppliers": len(SUPPLIERS), **preview(anchor)}
    with session.begin():
        session.execute(select(func.pg_advisory_xact_lock(1430082, 1)))
        actor = session.scalar(select(User).where(User.email == admin_email.strip().lower()))
        if actor is None or actor.role != "ADMIN" or not actor.is_active:
            raise DomainError(
                403, "FORBIDDEN", "Cần tài khoản Admin đang hoạt động để tạo dữ liệu mẫu."
            )
        marker = session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "DEMO_DATA_IMPORTED",
                AuditLog.target_id == DATASET_ID,
            )
        )
        if marker:
            return {
                "status": "already_imported",
                "version": VERSION,
                "message": "Bộ mẫu đã tồn tại; giữ nguyên mọi thay đổi sau đó.",
            }
        collisions = session.scalars(
            select(Product.sku).where(Product.sku.in_([spec.sku for spec in PRODUCTS]))
        ).all()
        category_names = ["[DEMO] " + name for name in CATEGORIES]
        if collisions or session.scalar(
            select(Category.id).where(Category.name.in_(category_names)).limit(1)
        ):
            raise DomainError(
                409,
                "DEMO_NAMESPACE_CONFLICT",
                "Có SKU hoặc danh mục trùng bộ mẫu. Không thay đổi dữ liệu hiện có.",
            )
        category_ids = [entity_id("category:" + str(i)) for i in range(len(CATEGORIES))]
        supplier_ids = [entity_id("supplier:" + str(i)) for i in range(len(SUPPLIERS))]
        session.add_all(
            [
                Category(id=cid, name=name, is_active=True)
                for cid, name in zip(category_ids, category_names)
            ]
        )
        session.add_all(
            [
                Supplier(
                    id=sid,
                    name="[DEMO] " + name,
                    email=f"demo-supplier-{i + 1}@example.com",
                    phone=None,
                    is_active=True,
                )
                for i, (sid, name) in enumerate(zip(supplier_ids, SUPPLIERS))
            ]
        )
        session.flush()
        for index, spec in enumerate(PRODUCTS):
            product_id = entity_id("product:" + spec.sku)
            payload = ProductCreate(
                sku=spec.sku,
                name=spec.name,
                category_id=category_ids[spec.category],
                default_supplier_id=supplier_ids[spec.category],
                unit=spec.unit,
                min_stock=spec.minimum,
                unit_cost_vnd=spec.cost,
                lead_time_days=spec.lead,
            )
            movements = plan_product(spec, index, anchor)
            created = anchor - timedelta(days=85)
            product = Product(
                id=product_id,
                **payload.model_dump(),
                is_active=True,
                created_at=created,
                updated_at=created,
            )
            product.balance = StockBalance(
                on_hand=spec.target, updated_at=movements[-1].occurred_at if movements else created
            )
            session.add(product)
            session.flush()
            for number, movement in enumerate(movements):
                require_movement_permission(actor.role, movement.movement_type)
                movement_id = entity_id(f"movement:{spec.sku}:{number}")
                data = MovementCreate(
                    product_id=product_id,
                    movement_type=movement.movement_type,
                    quantity=str(movement.quantity),
                    reason=movement.reason,
                    supplier_id=supplier_ids[spec.category]
                    if movement.movement_type == "IN"
                    else None,
                    reference_code=f"DEMO-{spec.code}-{number:03d}",
                )
                session.add(
                    StockMovement(
                        id=movement_id,
                        actor_id=actor.id,
                        **data.model_dump(),
                        stock_before=movement.before,
                        stock_after=movement.after,
                        occurred_at=movement.occurred_at,
                        idempotency_key=str(movement_id),
                        request_fingerprint=request_fingerprint(data, actor.id),
                    )
                )
                if movement.movement_type.startswith("ADJUST"):
                    record_event(
                        session,
                        "STOCK_ADJUSTED",
                        actor_id=actor.id,
                        target_type="stock_movement",
                        target_id=movement_id,
                        details={
                            "product_id": str(product_id),
                            "movement_type": movement.movement_type,
                            "quantity": str(movement.quantity),
                        },
                    )
            if not spec.active:
                product.is_active = False
                product.updated_at = anchor
                record_event(
                    session,
                    "PRODUCT_ARCHIVED",
                    actor_id=actor.id,
                    target_type="product",
                    target_id=product_id,
                    details={"sku": spec.sku},
                )
        session.get(Category, category_ids[-1]).is_active = False
        session.get(Supplier, supplier_ids[-1]).is_active = False
        record_event(
            session,
            "DEMO_DATA_IMPORTED",
            actor_id=actor.id,
            target_type="demo_dataset",
            target_id=DATASET_ID,
            details={
                "version": VERSION,
                "products": report["products"],
                "movements": report["movements"],
                "categories": report["categories"],
                "suppliers": report["suppliers"],
            },
        )
    return {"status": "imported", "version": VERSION, **report}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or explicitly import labeled demo inventory."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Import the demo dataset into the local database"
    )
    parser.add_argument("--admin-email")
    args = parser.parse_args()
    engine = None
    try:
        if not args.apply:
            result = {
                "status": "preview",
                "categories": len(CATEGORIES),
                "suppliers": len(SUPPLIERS),
                **preview(datetime.now(UTC) - timedelta(hours=4)),
            }
        else:
            settings = Settings()
            if make_url(settings.database_url.get_secret_value()).host not in {
                "localhost",
                "127.0.0.1",
                "::1",
                "db",
            }:
                raise DomainError(
                    400, "DEMO_LOCAL_ONLY", "Bộ mẫu chỉ được nhập vào database local."
                )
            local = dotenv_values(PROJECT_ROOT / ".env")
            email = args.admin_email or os.getenv("ADMIN_EMAIL") or local.get("ADMIN_EMAIL")
            if not email:
                raise DomainError(
                    400,
                    "ADMIN_EMAIL_REQUIRED",
                    "Cần chỉ định Admin bằng --admin-email hoặc ADMIN_EMAIL.",
                )
            engine = build_engine(settings)
            with Session(engine) as session:
                result = import_demo(session, email)
    except DomainError as exc:
        result = {"status": "error", "code": exc.code, "message": exc.message}
    except ValidationError:
        result = {"status": "error", "code": "DEMO_CONFIG_INVALID"}
    except Exception:
        result = {
            "status": "error",
            "code": "DEMO_IMPORT_FAILED",
            "message": "Không nhập được bộ mẫu; transaction đã rollback.",
        }
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(result, ensure_ascii=True))
    return 2 if result["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
