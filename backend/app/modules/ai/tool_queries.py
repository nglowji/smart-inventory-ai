from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import Product, StockBalance
from app.modules.ai.policies import fold_text

ACCENTED = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
PLAIN = "".join(fold_text(letter) for letter in ACCENTED)
STOCK_COLUMNS = (
    Product.sku,
    Product.name,
    Product.unit,
    Product.is_active,
    Product.min_stock,
    Product.lead_time_days,
    StockBalance.on_hand,
)
STOCK = select(*STOCK_COLUMNS).join(StockBalance, StockBalance.product_id == Product.id)


def contains_text(column, value):
    return func.translate(func.lower(column), ACCENTED, PLAIN).contains(
        fold_text(value), autoescape=True
    )


def stock_row(session, sku):
    return session.execute(STOCK.where(Product.sku == sku)).mappings().first()


def encode_row(row):
    return {
        key: format(value, "f")
        if isinstance(value, Decimal)
        else value.isoformat()
        if isinstance(value, datetime)
        else value
        for key, value in row.items()
    }
