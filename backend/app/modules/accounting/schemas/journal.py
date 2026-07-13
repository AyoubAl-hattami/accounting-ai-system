from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


JournalStatus = Literal["draft", "reviewed", "posted", "void", "reversed"]


class JournalLineBase(BaseModel):
    account_id: int = Field(..., ge=1)

    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)

    description: str | None = None

    @model_validator(mode="after")
    def validate_debit_or_credit_only(self):
        if self.debit > 0 and self.credit > 0:
            raise ValueError("A journal line cannot have both debit and credit")

        if self.debit == 0 and self.credit == 0:
            raise ValueError("A journal line must have either debit or credit")

        return self


class JournalLineCreate(JournalLineBase):
    pass


class JournalLineRead(JournalLineBase):
    id: int
    journal_entry_id: int
    company_id: int
    line_no: int

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JournalEntryCreate(BaseModel):
    company_id: int = Field(..., ge=1)

    entry_no: str = Field(..., min_length=1, max_length=50)
    entry_date: date

    description: str | None = None

    source_type: str | None = Field(default=None, max_length=50)
    source_id: str | None = Field(default=None, max_length=100)

    lines: list[JournalLineCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_balanced_entry(self):
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)

        if total_debit <= 0:
            raise ValueError("Total debit must be greater than zero")

        if total_debit != total_credit:
            raise ValueError("Journal entry must be balanced: total debit must equal total credit")

        return self


class JournalEntryUpdate(BaseModel):
    entry_date: date | None = None
    description: str | None = None

    source_type: str | None = Field(default=None, max_length=50)
    source_id: str | None = Field(default=None, max_length=100)


class JournalEntryRead(BaseModel):
    id: int

    company_id: int
    fiscal_year_id: int
    fiscal_period_id: int

    entry_no: str
    entry_date: date

    description: str | None = None

    status: JournalStatus

    source_type: str | None = None
    source_id: str | None = None
    created_by_user_id: int | None = None
    creator_name: str | None = None

    reversal_of_id: int | None = None
    posted_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    lines: list[JournalLineRead] = []

    model_config = ConfigDict(from_attributes=True)
class JournalEntryReverseCreate(BaseModel):
    entry_no: str = Field(..., min_length=1, max_length=50)
    entry_date: date

    description: str | None = None
class OpeningBalanceLineCreate(BaseModel):
    account_id: int = Field(..., ge=1)

    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)

    description: str | None = None

    @model_validator(mode="after")
    def validate_debit_or_credit_only(self):
        if self.debit > 0 and self.credit > 0:
            raise ValueError("An opening balance line cannot have both debit and credit")

        if self.debit == 0 and self.credit == 0:
            raise ValueError("An opening balance line must have either debit or credit")

        return self


class OpeningBalanceCreate(BaseModel):
    company_id: int = Field(..., ge=1)

    entry_no: str = Field(..., min_length=1, max_length=50)
    entry_date: date

    description: str | None = "Opening balances"

    lines: list[OpeningBalanceLineCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_balanced_opening_balance(self):
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)

        if total_debit <= 0:
            raise ValueError("Total debit must be greater than zero")

        if total_debit != total_credit:
            raise ValueError(
                "Opening balance must be balanced: total debit must equal total credit"
            )

        return self