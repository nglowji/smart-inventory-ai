from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

Role = Literal["ADMIN", "STAFF", "VIEWER"]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    role: Role

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role | None = None
    is_active: bool | None = Field(default=None, strict=True)
    password: SecretStr | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value
