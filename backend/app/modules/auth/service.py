from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.passwords import Passwords
from app.db.models import User
from app.modules.audit.service import record_event
from app.modules.auth.schemas import Login, PasswordChange

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
        record_event(
            session,
            "LOGIN_FAILED",
            actor_id=None,
            target_type="auth",
            details={"reason": "invalid_credentials"},
        )
        session.commit()
        raise DomainError(401, "UNAUTHORIZED", "Email hoặc mật khẩu không đúng.")
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "ver": user.auth_version,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        key,
        algorithm="HS256",
    )
    record_event(session, "LOGIN_SUCCESS", actor_id=user.id, target_type="user", target_id=user.id)
    session.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role}


def change_password(session: Session, actor: User, payload: PasswordChange) -> None:
    user = session.scalar(
        select(User)
        .where(User.id == actor.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not user.is_active or not passwords.verify(
        payload.current_password.get_secret_value(), user.password_hash
    ):
        raise DomainError(400, "CURRENT_PASSWORD_INVALID", "Mật khẩu hiện tại không đúng.")
    if payload.current_password.get_secret_value() == payload.new_password.get_secret_value():
        raise DomainError(422, "PASSWORD_UNCHANGED", "Mật khẩu mới cần khác mật khẩu hiện tại.")
    user.password_hash = passwords.hash(payload.new_password.get_secret_value())
    user.auth_version += 1
    record_event(
        session, "PASSWORD_CHANGED", actor_id=user.id, target_type="user", target_id=user.id
    )
    session.commit()
