from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.passwords import Passwords
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["Authentication"])
passwords = Passwords()
dummy_hash = passwords.hash("dummy-value-only-for-timing")
bearer = HTTPBearer(auto_error=False)


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


def signing_key(request: Request) -> str:
    secret = request.app.state.settings.jwt_secret
    if secret is None:
        raise DomainError(503, "AUTH_NOT_CONFIGURED", "Chưa cấu hình khóa đăng nhập.")
    return secret.get_secret_value()


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
            signing_key(request),
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


@router.post("/login")
def login(payload: Login, request: Request, session: Session = Depends(get_session)):
    key = signing_key(request)
    user = session.scalar(select(User).where(User.email == str(payload.email).strip().lower()))
    valid = passwords.verify(payload.password, user.password_hash if user else dummy_hash)
    if not valid or user is None or not user.is_active:
        raise DomainError(401, "UNAUTHORIZED", "Email hoặc mật khẩu không đúng.")
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=request.app.state.settings.access_token_minutes),
        },
        key,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}
