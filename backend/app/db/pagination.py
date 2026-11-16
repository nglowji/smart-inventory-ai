from sqlalchemy import func, select
from sqlalchemy.orm import Session


def paginate(session: Session, statement, page: int, page_size: int):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    items = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}
