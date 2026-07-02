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
