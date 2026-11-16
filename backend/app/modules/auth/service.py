from datetime import UTC, datetime, timedelta

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
        raise DomainError(503, "AUTH_NOT_CONFIGURED", "Chưa cấu hình khóa đăng nhập.")
    return settings.jwt_secret.get_secret_value()


def authenticate(payload: Login, settings: Settings, session: Session):
    key = signing_key(settings)
    user = session.scalar(select(User).where(User.email == str(payload.email).strip().lower()))
    valid = passwords.verify(payload.password, user.password_hash if user else dummy_hash)
    if not valid or user is None or not user.is_active:
        raise DomainError(401, "UNAUTHORIZED", "Email hoặc mật khẩu không đúng.")
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        key,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role}
