from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.identity import normalize_email
from app.modules.accounting.schemas.company_user import CompanyRole
from app.modules.accounting.schemas.user import validate_password_strength


class CompanyUserInvitationCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    email: EmailStr
    role: CompanyRole = "viewer"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_identity(cls, value: str) -> str:
        return normalize_email(str(value))


class CompanyUserInvitationResponse(BaseModel):
    status: str
    message: str
    invite_url: str | None = None
    token: str | None = None


class CompanyUserInvitationValidateResponse(BaseModel):
    valid: bool
    email: str
    role: CompanyRole
    company_name: str
    user_exists: bool


class CompanyUserInvitationAccept(BaseModel):
    token: str
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_optional_password(cls, value: str | None) -> str | None:
        return validate_password_strength(value) if value is not None else None


class CompanyUserInvitationRead(BaseModel):
    id: int
    company_id: int
    email: EmailStr
    role: CompanyRole
    invited_by_user_id: int
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_by_user_id: int | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: int | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
