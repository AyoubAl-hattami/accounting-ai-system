from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CompanyRole = Literal[
    "admin",
    "accountant",
    "reviewer",
    "approver",
    "auditor",
    "viewer",
]


class CompanyUserCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    role: CompanyRole = "viewer"
    is_active: bool = True


class CompanyUserUpdate(BaseModel):
    role: CompanyRole | None = None
    is_active: bool | None = None


class CompanyUserRead(BaseModel):
    id: int

    company_id: int
    user_id: int

    role: CompanyRole
    is_active: bool

    created_at: datetime
    updated_at: datetime

    user_email: str | None = None
    user_full_name: str | None = None
    user_is_active: bool = True

    model_config = ConfigDict(from_attributes=True)