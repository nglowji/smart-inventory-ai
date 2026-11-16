from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import User
from app.db.session import get_session
from app.modules.auth.service import signing_key

bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise DomainError(401, "UNAUTHORIZED", "Vui lòng đăng nhập.")
    try:
        claims = jwt.decode(
            credentials.credentials,
            signing_key(request.app.state.settings),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise DomainError(401, "UNAUTHORIZED", "Phiên đăng nhập không hợp lệ.") from None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise DomainError(401, "UNAUTHORIZED", "Phiên đăng nhập không hợp lệ.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise DomainError(403, "FORBIDDEN", "Chỉ Admin được thực hiện thao tác này.")
    return user
