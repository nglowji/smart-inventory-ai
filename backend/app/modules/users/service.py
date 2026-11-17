from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import User
from app.modules.audit.service import record_event
from app.modules.auth.service import passwords
from app.modules.users.schemas import UserCreate, UserPatch

ACCOUNT_MANAGEMENT_LOCK = 913574203


def lock_admin_management(session: Session, actor: User) -> None:
    # Administrative writes are rare. Serialize them across workers to protect the last admin.
    session.execute(select(func.pg_advisory_xact_lock(ACCOUNT_MANAGEMENT_LOCK)))
    session.refresh(actor)
    if not actor.is_active or actor.role != "ADMIN":
        raise DomainError(403, "FORBIDDEN", "Bạn không còn quyền quản trị tài khoản.")


def create_user(session: Session, actor: User, payload: UserCreate) -> User:
    lock_admin_management(session, actor)
    user = User(
        id=uuid4(),
        email=str(payload.email),
        role=payload.role,
        password_hash=passwords.hash(payload.password.get_secret_value()),
    )
    session.add(user)
    record_event(
        session,
        "USER_CREATED",
        actor_id=actor.id,
        target_type="user",
        target_id=user.id,
        details={"role": user.role},
    )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", "") == "uq_users_email":
            raise DomainError(409, "EMAIL_ALREADY_EXISTS", "Email đã được sử dụng.") from None
        raise
    session.refresh(user)
    return user


def update_user(session: Session, actor: User, user_id: UUID, payload: UserPatch) -> User:
    lock_admin_management(session, actor)
    user = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise DomainError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản.")
    next_role = payload.role if payload.role is not None else user.role
    next_active = payload.is_active if payload.is_active is not None else user.is_active
    if user.role == "ADMIN" and user.is_active and (next_role != "ADMIN" or not next_active):
        active_admins = session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "ADMIN", User.is_active.is_(True))
        )
        if active_admins <= 1:
            raise DomainError(409, "LAST_ADMIN", "Phải giữ ít nhất một Admin đang hoạt động.")
    changed = next_role != user.role or next_active != user.is_active
    if changed:
        record_event(
            session,
            "USER_UPDATED",
            actor_id=actor.id,
            target_type="user",
            target_id=user.id,
            details={
                "old_role": user.role,
                "new_role": next_role,
                "old_active": user.is_active,
                "new_active": next_active,
            },
        )
    user.role, user.is_active = next_role, next_active
    if payload.password is not None:
        user.password_hash = passwords.hash(payload.password.get_secret_value())
        record_event(
            session, "USER_PASSWORD_RESET", actor_id=actor.id, target_type="user", target_id=user.id
        )
    if changed or payload.password is not None:
        user.auth_version += 1
    session.commit()
    session.refresh(user)
    return user
