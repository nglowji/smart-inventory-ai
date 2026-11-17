from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.pagination import paginate


def list_users(session: Session, page: int, page_size: int, search: str | None):
    statement = select(User)
    if search:
        statement = statement.where(User.email.icontains(search.strip(), autoescape=True))
    return paginate(session, statement.order_by(User.email, User.id), page, page_size)
