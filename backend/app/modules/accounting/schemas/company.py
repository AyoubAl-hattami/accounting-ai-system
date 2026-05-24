from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)

    registration_no: str | None = Field(default=None, max_length=100)
    tax_no: str | None = Field(default=None, max_length=100)

    base_currency: str = Field(default="USD", min_length=3, max_length=3)

    address: str | None = None
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)

    registration_no: str | None = Field(default=None, max_length=100)
    tax_no: str | None = Field(default=None, max_length=100)

    base_currency: str | None = Field(default=None, min_length=3, max_length=3)

    address: str | None = None
    is_active: bool | None = None


class CompanyRead(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)