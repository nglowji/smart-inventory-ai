from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.schemas import Page
from app.db.models import User
from app.db.session import get_session
from app.modules.auth.dependencies import admin_user
from app.modules.users.queries import list_users
from app.modules.users.schemas import UserCreate, UserPatch, UserRead
from app.modules.users.service import create_user, update_user

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(admin_user)])


@router.get("", response_model=Page[UserRead])
def users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    session: Session = Depends(get_session),
):
    return list_users(session, page, page_size, search)


@router.post("", response_model=UserRead, status_code=201)
def add_user(
    payload: UserCreate, actor: User = Depends(admin_user), session: Session = Depends(get_session)
):
    return create_user(session, actor, payload)


@router.patch("/{user_id}", response_model=UserRead)
def edit_user(
    user_id: UUID,
    payload: UserPatch,
    actor: User = Depends(admin_user),
    session: Session = Depends(get_session),
):
    return update_user(session, actor, user_id, payload)
