"""Explicit local admin seed. No public registration or default password."""

import getpass
import os

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.connection import build_engine
from app.db.models import User
from app.modules.auth.api import passwords


def main():
    email = (
        str(
            TypeAdapter(EmailStr).validate_python(
                os.environ.get("ADMIN_EMAIL") or input("Admin email: ")
            )
        )
        .strip()
        .lower()
    )
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password (12+ chars): ")
    if len(password) < 12:
        raise SystemExit("Password must have at least 12 characters.")
    engine = build_engine(Settings())
    try:
        with Session(engine) as session, session.begin():
            if session.scalar(select(User.id).where(User.email == email)):
                raise SystemExit("User already exists; no changes made.")
            session.add(User(email=email, password_hash=passwords.hash(password), role="ADMIN"))
        print("Admin created. Password was not logged.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
