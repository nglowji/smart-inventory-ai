from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
