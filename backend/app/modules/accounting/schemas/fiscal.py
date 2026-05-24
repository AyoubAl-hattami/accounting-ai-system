from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FiscalStatus = Literal["open", "closed", "locked"]


class FiscalYearBase(BaseModel):
    company_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=100)

    start_date: date
    end_date: date

    status: FiscalStatus = "open"

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class FiscalYearCreate(FiscalYearBase):
    pass


class FiscalYearUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)

    start_date: date | None = None
    end_date: date | None = None

    status: FiscalStatus | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class FiscalYearRead(FiscalYearBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FiscalPeriodBase(BaseModel):
    company_id: int = Field(..., ge=1)
    fiscal_year_id: int = Field(..., ge=1)

    period_no: int = Field(..., ge=1, le=12)
    name: str = Field(..., min_length=1, max_length=100)

    start_date: date
    end_date: date

    status: FiscalStatus = "open"

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class FiscalPeriodCreate(FiscalPeriodBase):
    pass


class FiscalPeriodUpdate(BaseModel):
    period_no: int | None = Field(default=None, ge=1, le=12)
    name: str | None = Field(default=None, min_length=1, max_length=100)

    start_date: date | None = None
    end_date: date | None = None

    status: FiscalStatus | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class FiscalPeriodRead(FiscalPeriodBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)