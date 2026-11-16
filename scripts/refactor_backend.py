"""One-shot extraction of transport-independent queries and serializers."""
from pathlib import Path
import ast
import re

root = Path(__file__).resolve().parents[1] / "backend" / "app"


def read(name):
    return (root / name).read_text(encoding="utf-8")


def write(name, text):
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def function(source, name):
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    return "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno]) + "\n"


inventory = read("modules/inventory/service.py")
dates = function(inventory, "date_bounds")
write("core/dates.py", 'from datetime import UTC, date, datetime, time, timedelta\nfrom zoneinfo import ZoneInfo\nfrom app.core.errors import DomainError\n\nLOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")\n\n\n' + dates)
serializer = function(inventory, "movement_output")
write("modules/inventory/serializers.py", 'from app.db.models import Product, StockMovement\n\n\n' + serializer)
inventory = inventory.replace(dates, "").replace(serializer, "")
inventory = inventory.replace('LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")', "")
inventory = inventory.replace("from datetime import UTC, date, datetime, time, timedelta", "from datetime import UTC, datetime")
inventory = inventory.replace("from zoneinfo import ZoneInfo\n", "")
inventory = inventory.replace("from app.modules.catalog.service import get_product\n", "")
inventory = inventory.replace("from app.modules.inventory.schemas import MovementCreate", "from app.modules.inventory.schemas import MovementCreate\nfrom app.modules.inventory.serializers import movement_output")
inventory = inventory.replace("product = get_product(session, payload.product_id, lock=True)", '''product = session.scalar(select(Product).where(Product.id == payload.product_id).with_for_update())
    if product is None:
        raise DomainError(404, "PRODUCT_NOT_FOUND", "Product not found.")''')
write("modules/inventory/service.py", inventory)

catalog = read("modules/catalog/service.py")
pagination = function(catalog, "paginate")
write("db/pagination.py", 'from sqlalchemy import func, select\nfrom sqlalchemy.orm import Session\n\n\n' + pagination)
product_serializer = function(catalog, "product_output")
write("modules/catalog/serializers.py", 'from app.db.models import Product\nfrom app.modules.catalog.schemas import ProductRead\n\n\n' + product_serializer)
catalog = catalog.replace(pagination, "").replace(product_serializer, "")
catalog = catalog.replace("from app.modules.catalog.schemas import ProductRead", "from app.modules.catalog.serializers import product_output")
write("modules/catalog/service.py", catalog)
catalog_api = read("modules/catalog/api.py").replace("from app.modules.catalog import service", "from app.modules.catalog import service\nfrom app.db.pagination import paginate\nfrom app.modules.catalog.serializers import product_output")
catalog_api = catalog_api.replace("service.paginate(", "paginate(").replace("service.product_output(", "product_output(")
write("modules/catalog/api.py", catalog_api)

source = read("modules/inventory/api.py")
balances = function(source, "balances")
history = function(source, "history")
balances = re.sub(r"def balances\([\s\S]*?\):\n", '''def list_balances(session: Session, *, page: int = 1, page_size: int = 20,
                  search: str | None = None, low_stock: bool = False,
                  active: bool | None = True, category_id: UUID | None = None):
''', balances, count=1)
history = re.sub(r"def history\([\s\S]*?\):\n", '''def list_movements(session: Session, *, page: int = 1, page_size: int = 20,
                   sku: str | None = None, movement_type: str | None = None,
                   date_from: date | None = None, date_to: date | None = None,
                   actor_id: UUID | None = None):
''', history, count=1)
query_imports = '''from datetime import date
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.dates import date_bounds
from app.db.models import Product, StockBalance, StockMovement, User
from app.db.pagination import paginate
from app.modules.catalog.serializers import product_output
from app.modules.inventory.serializers import movement_output
'''
write("modules/inventory/queries.py", query_imports + "\n\n" + balances + "\n\n" + history)
# Keep the public endpoint signatures and replace SQL bodies with explicit query calls.
for name, code, call in (("balances", function(source, "balances"),
                         "return list_balances(session, page=page, page_size=page_size, search=search, low_stock=low_stock, active=active, category_id=category_id)"),
                        ("history", function(source, "history"),
                         "return list_movements(session, page=page, page_size=page_size, sku=sku, movement_type=movement_type, date_from=date_from, date_to=date_to, actor_id=actor_id)")):
    signature = code[:code.index("):\n") + 3]
    source = source.replace(code, signature + "    " + call + "\n")
source = source.replace("from sqlalchemy import func, select\n", "").replace("from sqlalchemy.orm import Session, joinedload", "from sqlalchemy.orm import Session")
source = source.replace("from app.db.models import Product, StockBalance, StockMovement, User", "from app.db.models import User")
source = source.replace("from app.modules.catalog.service import paginate, product_output\n", "")
source = source.replace("from app.modules.inventory.service import date_bounds, movement_output, post_movement", "from app.modules.inventory.service import post_movement\nfrom app.modules.inventory.queries import list_balances, list_movements")
write("modules/inventory/api.py", source)

reports = read("modules/reporting/api.py")
queries = reports.replace("from fastapi import APIRouter, Depends\n", "")
queries = queries.replace("from app.db.session import get_session\n", "").replace("from app.modules.auth.api import current_user\n", "")
queries = queries.replace("from app.modules.inventory.service import LOCAL_ZONE, date_bounds", "from app.core.dates import LOCAL_ZONE, date_bounds")
queries = re.sub(r"router = APIRouter\([^\n]+\)\n", "", queries)
queries = re.sub(r'@router.get\([^\n]+\)\n', "", queries)
for name in ("summary", "flow"):
    queries = re.sub(rf"def {name}\([\s\S]*?\):\n", f"def get_{name}(session: Session, date_from: date | None = None, date_to: date | None = None):\n", queries, count=1)
write("modules/reporting/queries.py", queries)
write("modules/reporting/api.py", '''from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.modules.auth.dependencies import current_user
from app.modules.reporting.queries import get_flow, get_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(current_user)])

@router.get("/summary")
def summary(date_from: date | None = None, date_to: date | None = None,
            session: Session = Depends(get_session)):
    return get_summary(session, date_from, date_to)

@router.get("/flow")
def flow(date_from: date | None = None, date_to: date | None = None,
         session: Session = Depends(get_session)):
    return get_flow(session, date_from, date_to)
''')

auth = read("modules/auth/api.py")
dependencies = "\n\n".join(function(auth, name) for name in ("signing_key", "current_user", "admin_user"))
write("modules/auth/dependencies.py", '''from uuid import UUID
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.errors import DomainError
from app.db.models import User
from app.db.session import get_session

bearer = HTTPBearer(auto_error=False)

''' + dependencies)
node = next(node for node in ast.parse(auth).body if isinstance(node, ast.ClassDef) and node.name == "Login")
login_schema = "\n".join(auth.splitlines()[node.lineno - 1:node.end_lineno])
write("modules/auth/schemas.py", 'from pydantic import BaseModel, ConfigDict, EmailStr, Field\n\n\n' + login_schema + "\n")
login = function(auth, "login")
login = re.sub(r"def login\([^\n]+\):", "def authenticate(payload: Login, settings: Settings, session: Session):", login, count=1)
login = login.replace("key = signing_key(request)", "key = signing_key(settings)").replace("request.app.state.settings.access_token_minutes", "settings.access_token_minutes")
write("modules/auth/service.py", '''from datetime import UTC, datetime, timedelta
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.errors import DomainError
from app.core.passwords import Passwords
from app.db.models import User
from app.modules.auth.schemas import Login

passwords = Passwords()
dummy_hash = passwords.hash("dummy-value-only-for-timing")

def signing_key(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise DomainError(503, "AUTH_NOT_CONFIGURED", "Authentication key is not configured.")
    return settings.jwt_secret.get_secret_value()

''' + login)
deps = read("modules/auth/dependencies.py")
deps = deps.replace(function(deps, "signing_key"), "")
deps = deps.replace("signing_key(request)", "signing_key(request.app.state.settings)")
deps = deps.replace("from app.db.session import get_session", "from app.db.session import get_session\nfrom app.modules.auth.service import signing_key")
write("modules/auth/dependencies.py", deps)
write("modules/auth/api.py", '''from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.models import User
from app.db.session import get_session
from app.modules.auth.dependencies import current_user
from app.modules.auth.schemas import Login
from app.modules.auth.service import authenticate

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(payload: Login, request: Request, session: Session = Depends(get_session)):
    return authenticate(payload, request.app.state.settings, session)

@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}
''')

for path in root.rglob("*.py"):
    text = path.read_text(encoding="utf-8")
    text = text.replace("from app.modules.auth.api import admin_user, current_user", "from app.modules.auth.dependencies import admin_user, current_user")
    text = text.replace("from app.modules.auth.api import current_user", "from app.modules.auth.dependencies import current_user")
    text = text.replace("from app.modules.auth.api import passwords", "from app.modules.auth.service import passwords")
    path.write_text(text, encoding="utf-8")
tests = root.parent / "tests" / "conftest.py"
tests.write_text(tests.read_text(encoding="utf-8").replace("from app.modules.auth.api import passwords", "from app.modules.auth.service import passwords"), encoding="utf-8")
