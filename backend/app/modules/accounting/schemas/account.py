from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AccountType = Literal[
    "asset",
    "liability",
    "equity",
    "income",
    "expense",
]


class AccountBase(BaseModel):
    company_id: int = Field(..., ge=1)

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)

    account_type: AccountType

    parent_id: int | None = Field(default=None, ge=1)
    description: str | None = None

    is_active: bool = True
    is_system: bool = False


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    account_type: AccountType | None = None

    parent_id: int | None = Field(default=None, ge=1)
    description: str | None = None

    is_active: bool | None = None
    is_system: bool | None = None


class AccountRead(AccountBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
class AccountSeedResult(BaseModel):
    company_id: int
    created_count: int
    skipped_count: int
    message: str
    accounts: list[AccountRead]