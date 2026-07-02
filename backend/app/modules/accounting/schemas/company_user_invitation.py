from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.accounting.schemas.company_user import CompanyRole


class CompanyUserInvitationCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    email: EmailStr
    role: CompanyRole = "viewer"


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
    password: str | None = None


class CompanyUserInvitationRead(BaseModel):
    id: int
    company_id: int
    email: EmailStr
    role: CompanyRole
    invited_by_user_id: int
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_by_user_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
