"""Platform-owner client onboarding.

Gated on ``get_current_platform_admin``, never on company membership: the
company being created does not exist yet, and the platform owner deliberately
never becomes a member of it.

The whole onboarding is one transaction.  Repositories flush, this route owns
the single ``db.commit()``, and any failure rolls the entire tenant back — a
client is either fully set up or not created at all.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.onboarding.dto import OnboardClientCommand
from app.application.onboarding.errors import (
    AdminEmailTaken,
    CompanyNameTaken,
    InvalidSubscriptionWindow,
    MissingTemporaryPassword,
    OnboardingError,
    ReusedAdminIsInactive,
    ReusedAdminIsPlatformAdmin,
)
from app.application.onboarding.handover import build_handover_message
from app.application.onboarding.passwords import (
    TEMPORARY_PASSWORD_LENGTH,
    generate_temporary_password,
)
from app.application.onboarding.use_cases import OnboardClient
from app.core.auth_dependencies import get_current_platform_admin
from app.core.database import get_db
from app.core.public_url import public_login_url
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.company_user_repository import (
    SqlAlchemyCompanyUserRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.fiscal_repository import (
    SqlAlchemyFiscalRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.client_onboarding import (
    DEFAULT_PLAN_CODE,
    SUGGESTED_CURRENCIES,
    SUGGESTED_PLAN_CODES,
    ClientOnboardingCreate,
    ClientOnboardingRead,
    OnboardingDefaultsRead,
)
from app.modules.accounting.services.audit_service import prepare_audit_log


router = APIRouter(
    prefix="/platform/onboarding",
    tags=["Platform Onboarding"],
)

# Each domain refusal maps to one HTTP answer.  409 means "this already exists,
# choose differently"; 422 means "the request itself does not make sense".
_ERROR_STATUS: dict[type[OnboardingError], int] = {
    CompanyNameTaken: status.HTTP_409_CONFLICT,
    AdminEmailTaken: status.HTTP_409_CONFLICT,
    ReusedAdminIsPlatformAdmin: status.HTTP_409_CONFLICT,
    ReusedAdminIsInactive: status.HTTP_409_CONFLICT,
    MissingTemporaryPassword: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InvalidSubscriptionWindow: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def _error_detail(error: OnboardingError) -> str:
    subject = str(error)
    if isinstance(error, CompanyNameTaken):
        return f"A company named '{subject}' already exists"
    if isinstance(error, AdminEmailTaken):
        return (
            f"An account already exists for {subject}. "
            "Set reuse_existing_user to attach it to this company."
        )
    if isinstance(error, ReusedAdminIsPlatformAdmin):
        return (
            "A platform administrator cannot be made a member of a client company"
        )
    if isinstance(error, ReusedAdminIsInactive):
        return (
            f"The account for {subject} is deactivated and must be reactivated "
            "before it can administer a company"
        )
    if isinstance(error, MissingTemporaryPassword):
        return (
            f"No account exists for {subject}, so a temporary password is required"
        )
    return f"Subscription would already be expired at {subject}"


@router.get("/defaults", response_model=OnboardingDefaultsRead)
def onboarding_defaults_endpoint(
    _admin: User = Depends(get_current_platform_admin),
):
    """Wizard defaults, so platform policy lives in one place."""
    return OnboardingDefaultsRead(
        suggested_currencies=list(SUGGESTED_CURRENCIES),
        suggested_plan_codes=list(SUGGESTED_PLAN_CODES),
        default_plan_code=DEFAULT_PLAN_CODE,
        expiry_presets=["1_month", "3_months", "1_year"],
        public_login_url=public_login_url(),
        generated_password_length=TEMPORARY_PASSWORD_LENGTH,
    )


@router.post(
    "/clients",
    response_model=ClientOnboardingRead,
    status_code=status.HTTP_201_CREATED,
)
def onboard_client_endpoint(
    payload: ClientOnboardingCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    generated_password = (
        generate_temporary_password() if payload.generate_password else None
    )
    # The plaintext lives in this local and in the response body only.  It is
    # hashed on the way into the database and never reaches the audit log.
    temporary_password = generated_password or payload.temporary_password or ""

    use_case = OnboardClient(
        companies=SqlAlchemyCompanyRepository(db),
        users=SqlAlchemyUserRepository(db),
        company_users=SqlAlchemyCompanyUserRepository(db),
        subscriptions=SqlAlchemySubscriptionRepository(db),
        accounts=SqlAlchemyAccountRepository(db),
        fiscal=SqlAlchemyFiscalRepository(db),
    )

    try:
        result = use_case.execute(
            OnboardClientCommand(
                company_name=payload.company_name,
                base_currency=payload.base_currency,
                admin_email=str(payload.admin_email),
                temporary_password=temporary_password,
                admin_full_name=payload.admin_full_name,
                plan_code=payload.plan_code,
                subscription_status=payload.subscription_status,
                subscription_expires_at=payload.subscription_expires_at,
                trial_ends_at=payload.trial_ends_at,
                seed_default_accounts=payload.seed_default_accounts,
                create_fiscal_year=payload.create_fiscal_year,
                open_monthly_periods=payload.open_monthly_periods,
                reuse_existing_user=payload.reuse_existing_user,
                onboarding_note=payload.onboarding_note,
            )
        )
    except OnboardingError as error:
        # Nothing is committed until the end of this handler, so rolling back
        # here guarantees a refused onboarding leaves no partial tenant.
        db.rollback()
        raise HTTPException(
            status_code=_ERROR_STATUS.get(
                type(error), status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=_error_detail(error),
        )

    # An existing account keeps its own credentials, so there is nothing to hand
    # over in that case.
    handover_password = (
        temporary_password if not result.admin_was_existing else None
    )
    login_url = public_login_url()

    prepare_audit_log(
        db=db,
        company_id=result.company_id,
        actor=admin.email,
        actor_user_id=admin.id,
        actor_email=admin.email,
        actor_name=admin.full_name,
        action="onboard_client",
        entity_type="client_onboarding",
        entity_id=result.company_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        # No password, generated or supplied, is ever recorded here.
        new_values={
            "company_name": result.company_name,
            "base_currency": result.base_currency,
            "admin_email": result.admin_email,
            "admin_user_id": result.admin_user_id,
            "admin_was_existing": result.admin_was_existing,
            "plan_code": result.plan_code,
            "subscription_status": result.subscription_status,
            "expires_at": (
                result.expires_at.isoformat() if result.expires_at else None
            ),
            "seeded_accounts_count": result.seeded_accounts_count,
            "fiscal_year_created": result.fiscal_year_created,
            "fiscal_periods_created": result.fiscal_periods_created,
            "onboarding_note": payload.onboarding_note,
        },
        description=(
            f"Onboarded client '{result.company_name}' with admin "
            f"{result.admin_email}"
        ),
    )
    db.commit()

    return ClientOnboardingRead(
        company_id=result.company_id,
        company_name=result.company_name,
        base_currency=result.base_currency,
        admin_user_id=result.admin_user_id,
        admin_email=result.admin_email,
        admin_was_existing=result.admin_was_existing,
        subscription_status=result.subscription_status,
        effective_status=result.effective_status,
        plan_code=result.plan_code,
        expires_at=result.expires_at,
        trial_ends_at=result.trial_ends_at,
        days_remaining=result.days_remaining,
        seeded_accounts_count=result.seeded_accounts_count,
        fiscal_year_created=result.fiscal_year_created,
        fiscal_periods_created=result.fiscal_periods_created,
        generated_password=handover_password,
        # A reused account keeps the password its owner already chose, so only a
        # freshly created admin is forced through the change screen.
        must_change_password=not result.admin_was_existing,
        public_login_url=login_url,
        handover_message=build_handover_message(
            company_name=result.company_name,
            admin_email=result.admin_email,
            temporary_password=handover_password,
            expires_at=result.expires_at,
            login_url=login_url,
        ),
    )
