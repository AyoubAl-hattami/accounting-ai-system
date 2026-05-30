from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(c.islower() for c in value):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )

        if not any(c.isupper() for c in value):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not any(c.isdigit() for c in value):
            raise ValueError(
                "Password must contain at least one digit"
            )

        return value


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None

    is_active: bool
    is_superuser: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str