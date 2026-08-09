"""Request and response contracts for platform client onboarding."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.identity import normalize_email
from app.modules.accounting.schemas.account import CHART_TEMPLATE_CODES, ChartTemplate
from app.modules.accounting.schemas.user import validate_password_strength


DEFAULT_PLAN_CODE = "monthly"

# Suggested only.  Company.base_currency is a free 3-letter code, so this list
# populates the wizard without narrowing what the API accepts.
SUGGESTED_CURRENCIES: tuple[str, ...] = (
    "USD",
    "EUR",
    "GBP",
    "SAR",
    "AED",
    "EGP",
    "MAD",
    "TND",
    "JOD",
    "QAR",
    "KWD",
)

SUGGESTED_PLAN_CODES: tuple[str, ...] = ("monthly", "quarterly", "yearly")


class ClientOnboardingCreate(BaseModel):
    """One client tenant, described in full."""

    company_name: str = Field(..., min_length=1, max_length=255)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)

    admin_email: EmailStr
    admin_full_name: str | None = Field(default=None, max_length=255)
    temporary_password: str | None = Field(default=None, min_length=8, max_length=128)
    generate_password: bool = False

    plan_code: str | None = Field(default=DEFAULT_PLAN_CODE, max_length=50)
    subscription_status: Literal["trial", "active"] = "active"
    subscription_expires_at: datetime | None = None
    trial_ends_at: datetime | None = None

    seed_default_accounts: bool = True
    chart_template: ChartTemplate = "default"
    create_fiscal_year: bool = True
    open_monthly_periods: bool = True

    reuse_existing_user: bool = False
    onboarding_note: str | None = Field(default=None, max_length=2000)

    @field_validator("admin_email", mode="before")
    @classmethod
    def normalize_email_identity(cls, value: str) -> str:
        return normalize_email(str(value))

    @field_validator("base_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("temporary_password")
    @classmethod
    def enforce_password_policy(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_password_strength(value)

    @model_validator(mode="after")
    def validate_onboarding_shape(self) -> "ClientOnboardingCreate":
        if self.temporary_password and self.generate_password:
            raise ValueError(
                "Choose either a temporary password or password generation, not both"
            )

        # Reuse is the one case where no password is needed: the existing
        # account keeps the credentials it already has.
        if (
            not self.temporary_password
            and not self.generate_password
            and not self.reuse_existing_user
        ):
            raise ValueError(
                "Supply temporary_password or set generate_password to true"
            )

        if self.subscription_expires_at is None and self.trial_ends_at is None:
            raise ValueError(
                "subscription_expires_at is required unless trial_ends_at is given"
            )

        return self


class ClientOnboardingRead(BaseModel):
    """Result of one onboarding.

    ``generated_password`` is the only place the plaintext ever appears — it is
    not stored, not written to the audit log, and cannot be read back later.
    """

    company_id: int
    company_name: str
    base_currency: str

    admin_user_id: int
    admin_email: str
    admin_was_existing: bool

    subscription_status: str
    effective_status: str
    plan_code: str | None = None
    expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
    days_remaining: int | None = None

    seeded_accounts_count: int = 0
    fiscal_year_created: bool = False
    fiscal_periods_created: int = 0

    generated_password: str | None = None
    must_change_password: bool = False
    public_login_url: str
    handover_message: str

    model_config = ConfigDict(from_attributes=True)


class OnboardingDefaultsRead(BaseModel):
    """Wizard defaults, so the frontend does not hard-code platform policy."""

    default_currency: str = "USD"
    suggested_currencies: list[str]
    default_plan_code: str = DEFAULT_PLAN_CODE
    suggested_plan_codes: list[str]
    default_subscription_status: str = "active"
    default_chart_template: str = "default"
    chart_templates: list[str]
    expiry_presets: list[str]
    # The real URL once APP_PUBLIC_URL is set, otherwise the placeholder, so the
    # wizard never has to decide which one to show.
    public_login_url: str
    generated_password_length: int
