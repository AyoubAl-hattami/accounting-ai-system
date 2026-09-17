from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AccountType = Literal[
    "asset",
    "liability",
    "equity",
    "income",
    "expense",
]

# Optional grouping hint chosen by the company.  Reports never read it — they
# classify by account_type — so a client is free to leave it unset.
AccountSubtype = Literal[
    "bank",
    "cash",
    "e_wallet",
    "receivable",
    "payable",
    "revenue",
    "expense",
    "other",
]


# Starter charts a company may seed.  "default" stays the default everywhere;
# regional templates are opt-in and every seeded account stays fully editable.
ChartTemplate = Literal["default", "yemen_cash_wallet"]

CHART_TEMPLATE_CODES: tuple[str, ...] = ("default", "yemen_cash_wallet")


class AccountBase(BaseModel):
    company_id: int = Field(..., ge=1)

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)

    account_type: AccountType
    account_subtype: AccountSubtype | None = None

    # The unit this account's balance is in. Omit it and the company's own
    # base_currency is used, so a single-currency book never has to think about
    # it. Stored upper-case; the database rejects anything else.
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    parent_id: int | None = Field(default=None, ge=1)
    description: str | None = None

    is_active: bool = True
    is_system: bool = False

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not cleaned.isalpha():
            raise ValueError("currency must be three letters, e.g. YER or USD")
        return cleaned


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    """Currency is deliberately absent.

    An account's currency is what every figure already posted to it is
    denominated in. Editing it would re-denominate history without touching a
    single amount -- 500 riyals would silently become 500 dollars. To hold a
    balance in another unit, open another account.
    """

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    account_type: AccountType | None = None
    account_subtype: AccountSubtype | None = None

    parent_id: int | None = Field(default=None, ge=1)
    description: str | None = None

    is_active: bool | None = None
    is_system: bool | None = None


class AccountRead(AccountBase):
    # Always present on the way out, even though it is optional on the way in:
    # by the time a row exists the company default has been resolved.
    currency: str

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