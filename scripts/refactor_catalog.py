from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1] / "backend/app/modules/catalog"
path = root / "api.py"
source = path.read_text(encoding="utf-8")


def function(name):
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    return "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno]) + "\n"


queries = '''from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.db.models import Category, Product, Supplier
from app.db.pagination import paginate
from app.modules.catalog.serializers import product_output
'''
for name, signature, call in (
    ("list_categories", "def list_categories(session: Session, page: int, page_size: int, active: bool | None):\n", "return queries.list_categories(session, page, page_size, active)"),
    ("list_suppliers", "def list_suppliers(session: Session, page: int, page_size: int, active: bool | None):\n", "return queries.list_suppliers(session, page, page_size, active)"),
    ("list_products", "def list_products(session: Session, page: int, page_size: int, search: str | None, active: bool | None, category_id: UUID | None):\n", "return queries.list_products(session, page, page_size, search, active, category_id)"),
):
    code = function(name)
    end = code.index("):\n") + 3
    queries += "\n\n" + signature + code[end:]
    source = source.replace(code, code[:end] + "    " + call + "\n")
(root / "queries.py").write_text(queries, encoding="utf-8")

for name, call in (
    ("create_category", "return service.save_category(session, payload.model_dump())"),
    ("patch_category", "return service.save_category(session, payload.model_dump(exclude_unset=True), category_id)"),
    ("create_supplier", "return service.save_supplier(session, payload.model_dump())"),
    ("patch_supplier", "return service.save_supplier(session, payload.model_dump(exclude_unset=True), supplier_id)"),
):
    code = function(name)
    end = code.index("):\n") + 3
    source = source.replace(code, code[:end] + "    " + call + "\n")
source = source.replace("from app.modules.catalog import service", "from app.modules.catalog import queries, service")
path.write_text(source, encoding="utf-8")
path = root / "service.py"
text = path.read_text(encoding="utf-8")
text += '''

def save_category(session: Session, data: dict, category_id: UUID | None = None) -> Category:
    category = require_record(session, Category, category_id) if category_id else Category()
    for key, value in data.items():
        setattr(category, key, value)
    session.add(category)
    commit_catalog(session)
    return category


def save_supplier(session: Session, data: dict, supplier_id: UUID | None = None) -> Supplier:
    supplier = require_record(session, Supplier, supplier_id) if supplier_id else Supplier()
    for key, value in data.items():
        setattr(supplier, key, value)
    session.add(supplier)
    commit_catalog(session)
    return supplier
'''
path.write_text(text, encoding="utf-8")
