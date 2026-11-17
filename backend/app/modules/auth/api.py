from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_session
from app.modules.auth.dependencies import current_user
from app.modules.auth.schemas import Login, PasswordChange
from app.modules.auth.service import authenticate, change_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
def login(payload: Login, request: Request, session: Session = Depends(get_session)):
    return authenticate(payload, request.app.state.settings, session)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/change-password")
def password_change(
    payload: PasswordChange,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    change_password(session, user, payload)
    return {"message": "Đã đổi mật khẩu. Vui lòng đăng nhập lại."}
