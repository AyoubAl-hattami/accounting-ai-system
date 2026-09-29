from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    is_customer: bool = False
    is_vendor: bool = False
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=50)
    address: str | None = None
    receivable_account_id: int | None = Field(default=None, ge=1)
    payable_account_id: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().upper()
        if len(stripped) != 3 or not stripped.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return stripped


class PartnerCreate(PartnerBase):
    company_id: int = Field(..., ge=1)


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    is_customer: bool | None = None
    is_vendor: bool | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=50)
    address: str | None = None
    receivable_account_id: int | None = Field(default=None, ge=1)
    payable_account_id: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class PartnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    code: str
    is_customer: bool
    is_vendor: bool
    currency: str
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None
    receivable_account_id: int | None = None
    payable_account_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerPageResponse(BaseModel):
    items: list[PartnerResponse]
    total: int
    skip: int
    limit: int
