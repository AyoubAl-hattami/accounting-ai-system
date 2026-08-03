"""Platform client onboarding: creation, isolation, and credential handling."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import requests
from sqlalchemy import func, select

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_subscription import CompanySubscription
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


ONBOARDING_ENDPOINT = "/platform/onboarding/clients"
BUSINESS_ENDPOINT = "/accounts"

# Every default account carries a unique code, so the seeded count is fixed.
DEFAULT_ACCOUNT_COUNT = 13
MONTHS_IN_YEAR = 12


def _headers(user):
    return {"Authorization": f"Bearer {create_user_token(user)}"}


def _url(base_url: str) -> str:
    return f"{base_url}{ONBOARDING_ENDPOINT}"


def _expiry(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _payload(factory, **overrides) -> dict:
    body = {
        "company_name": f"Onboard Co {uuid4().hex[:10]}",
        "base_currency": "USD",
        "admin_email": factory.unique_email("client-admin"),
        "admin_full_name": "Client Admin",
        "generate_password": True,
        "plan_code": "monthly",
        "subscription_status": "active",
        "subscription_expires_at": _expiry(),
    }
    body.update(overrides)
    return body


@pytest.fixture
def platform_admin(accounting_factory):
    user = accounting_factory.create_superuser()
    accounting_factory.db.commit()
    return user


@pytest.fixture
def tenant(accounting_factory):
    """An existing company with an admin member, used for the 403 cases."""
    company = accounting_factory.create_company(name=f"Tenant Co {uuid4().hex[:8]}")
    user = accounting_factory.create_user(full_name="Tenant Admin")
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="active")
    accounting_factory.db.commit()
    return company, user


@pytest.fixture
def onboarded(base_url, accounting_factory, platform_admin):
    """One successfully onboarded client, with the request that produced it."""
    body = _payload(accounting_factory)
    response = requests.post(_url(base_url), json=body, headers=_headers(platform_admin))
    assert response.status_code == 201, response.text
    return body, response.json()


# ── authorisation ─────────────────────────────────────────────────────────────


def test_platform_admin_can_onboard_a_client(base_url, accounting_factory, platform_admin):
    body = _payload(accounting_factory)

    response = requests.post(_url(base_url), json=body, headers=_headers(platform_admin))

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["company_name"] == body["company_name"]
    assert result["admin_email"] == body["admin_email"]
    assert result["admin_was_existing"] is False
    assert result["company_id"] > 0
    assert result["admin_user_id"] > 0
    assert result["effective_status"] == "active"


def test_company_admin_cannot_onboard_a_client(base_url, accounting_factory, tenant):
    _, company_admin = tenant

    response = requests.post(
        _url(base_url),
        json=_payload(accounting_factory),
        headers=_headers(company_admin),
    )

    assert response.status_code == 403


def test_normal_user_cannot_onboard_a_client(base_url, accounting_factory):
    outsider = accounting_factory.create_user()
    accounting_factory.db.commit()

    response = requests.post(
        _url(base_url),
        json=_payload(accounting_factory),
        headers=_headers(outsider),
    )

    assert response.status_code == 403


def test_onboarding_requires_authentication(base_url, accounting_factory):
    response = requests.post(_url(base_url), json=_payload(accounting_factory))

    assert response.status_code in (401, 403)


def test_onboarding_defaults_require_platform_admin(base_url, tenant):
    _, company_admin = tenant

    denied = requests.get(
        f"{base_url}/platform/onboarding/defaults", headers=_headers(company_admin)
    )

    assert denied.status_code == 403


# ── conflicts and validation ──────────────────────────────────────────────────


def test_duplicate_company_name_is_rejected(base_url, accounting_factory, onboarded):
    body, _ = onboarded
    platform_admin = accounting_factory.create_superuser()
    accounting_factory.db.commit()

    response = requests.post(
        _url(base_url),
        json=_payload(accounting_factory, company_name=body["company_name"]),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 409
    assert body["company_name"] in response.json()["detail"]


def test_duplicate_admin_email_is_rejected(base_url, accounting_factory, onboarded):
    body, _ = onboarded
    platform_admin = accounting_factory.create_superuser()
    accounting_factory.db.commit()

    response = requests.post(
        _url(base_url),
        json=_payload(accounting_factory, admin_email=body["admin_email"]),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 409
    assert "reuse_existing_user" in response.json()["detail"]


def test_a_refused_onboarding_creates_no_company(
    base_url, accounting_factory, platform_admin, onboarded
):
    """The whole onboarding is one transaction, so a late refusal rolls back."""
    body, _ = onboarded
    doomed_name = f"Rolled Back Co {uuid4().hex[:10]}"

    response = requests.post(
        _url(base_url),
        json=_payload(
            accounting_factory,
            company_name=doomed_name,
            admin_email=body["admin_email"],
        ),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 409
    assert (
        accounting_factory.db.scalar(
            select(Company).where(Company.name == doomed_name)
        )
        is None
    )


def test_an_already_expired_subscription_is_rejected(
    base_url, accounting_factory, platform_admin
):
    response = requests.post(
        _url(base_url),
        json=_payload(accounting_factory, subscription_expires_at=_expiry(days=-1)),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 422


def test_a_weak_supplied_password_is_rejected(
    base_url, accounting_factory, platform_admin
):
    response = requests.post(
        _url(base_url),
        json=_payload(
            accounting_factory,
            generate_password=False,
            temporary_password="alllowercase",
        ),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 422


def test_a_missing_expiry_is_rejected(base_url, accounting_factory, platform_admin):
    body = _payload(accounting_factory)
    del body["subscription_expires_at"]

    response = requests.post(_url(base_url), json=body, headers=_headers(platform_admin))

    assert response.status_code == 422


# ── credentials ───────────────────────────────────────────────────────────────


def test_generated_password_is_returned_once(base_url, platform_admin, onboarded):
    _, result = onboarded
    generated = result["generated_password"]

    assert generated
    assert len(generated) >= 8
    assert generated in result["handover_message"]

    # The tenant is readable afterwards through the platform surface, but the
    # credential is not part of any later projection.
    later = requests.get(
        f"{base_url}/platform/subscriptions/{result['company_id']}",
        headers=_headers(platform_admin),
    )
    assert later.status_code == 200
    assert generated not in later.text


def test_password_is_not_stored_in_plaintext(accounting_factory, onboarded):
    _, result = onboarded
    generated = result["generated_password"]

    admin = accounting_factory.db.scalar(
        select(User).where(User.id == result["admin_user_id"])
    )
    assert admin is not None
    assert admin.hashed_password != generated
    assert generated not in admin.hashed_password


def test_audit_log_records_the_onboarding_without_the_password(
    accounting_factory, onboarded
):
    _, result = onboarded
    generated = result["generated_password"]

    log = accounting_factory.db.scalar(
        select(AuditLog)
        .where(AuditLog.company_id == result["company_id"])
        .where(AuditLog.action == "onboard_client")
        .where(AuditLog.entity_type == "client_onboarding")
    )

    assert log is not None
    assert log.new_values["admin_email"] == result["admin_email"]
    assert log.new_values["plan_code"] == "monthly"
    assert log.new_values["expires_at"] is not None
    assert generated not in str(log.new_values)
    assert generated not in (log.description or "")


def test_created_client_admin_can_authenticate(base_url, onboarded):
    body, result = onboarded

    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": body["admin_email"], "password": result["generated_password"]},
    )

    assert login.status_code == 200, login.text
    me = requests.get(
        f"{base_url}/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == body["admin_email"]
    assert me.json()["is_superuser"] is False


# ── what onboarding actually created ──────────────────────────────────────────


def test_subscription_row_is_created_for_the_new_company(accounting_factory, onboarded):
    _, result = onboarded

    subscription = accounting_factory.db.scalar(
        select(CompanySubscription).where(
            CompanySubscription.company_id == result["company_id"]
        )
    )

    assert subscription is not None
    assert subscription.status == "active"
    assert subscription.plan_code == "monthly"
    assert subscription.expires_at is not None
    assert result["days_remaining"] is not None


def test_default_accounts_are_seeded_without_duplicates(accounting_factory, onboarded):
    _, result = onboarded

    codes = accounting_factory.db.scalars(
        select(Account.code).where(Account.company_id == result["company_id"])
    ).all()

    assert result["seeded_accounts_count"] == DEFAULT_ACCOUNT_COUNT
    assert len(codes) == DEFAULT_ACCOUNT_COUNT
    assert len(set(codes)) == DEFAULT_ACCOUNT_COUNT


def test_fiscal_year_and_monthly_periods_are_created_without_duplicates(
    accounting_factory, onboarded
):
    _, result = onboarded

    years = accounting_factory.db.scalars(
        select(FiscalYear).where(FiscalYear.company_id == result["company_id"])
    ).all()
    period_numbers = accounting_factory.db.scalars(
        select(FiscalPeriod.period_no).where(
            FiscalPeriod.company_id == result["company_id"]
        )
    ).all()

    assert result["fiscal_year_created"] is True
    assert result["fiscal_periods_created"] == MONTHS_IN_YEAR
    assert len(years) == 1
    assert years[0].status == "open"
    assert sorted(period_numbers) == list(range(1, MONTHS_IN_YEAR + 1))


def test_optional_accounting_setup_can_be_skipped(
    base_url, accounting_factory, platform_admin
):
    response = requests.post(
        _url(base_url),
        json=_payload(
            accounting_factory,
            seed_default_accounts=False,
            create_fiscal_year=False,
        ),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["seeded_accounts_count"] == 0
    assert result["fiscal_year_created"] is False
    assert result["fiscal_periods_created"] == 0
    assert (
        accounting_factory.db.scalar(
            select(func.count())
            .select_from(Account)
            .where(Account.company_id == result["company_id"])
        )
        == 0
    )


# ── isolation ─────────────────────────────────────────────────────────────────


def test_platform_admin_is_not_a_member_of_the_new_company(
    accounting_factory, platform_admin, base_url
):
    body = _payload(accounting_factory)
    response = requests.post(_url(base_url), json=body, headers=_headers(platform_admin))
    assert response.status_code == 201, response.text
    result = response.json()

    members = accounting_factory.db.scalars(
        select(CompanyUser).where(CompanyUser.company_id == result["company_id"])
    ).all()

    assert [member.user_id for member in members] == [result["admin_user_id"]]
    assert platform_admin.id not in {member.user_id for member in members}


def test_created_client_admin_is_admin_of_that_company_only(
    accounting_factory, onboarded
):
    _, result = onboarded

    memberships = accounting_factory.db.scalars(
        select(CompanyUser).where(CompanyUser.user_id == result["admin_user_id"])
    ).all()

    assert len(memberships) == 1
    assert memberships[0].company_id == result["company_id"]
    assert memberships[0].role == "admin"
    assert memberships[0].is_active is True


def test_created_client_admin_sees_only_its_own_company(
    base_url, accounting_factory, onboarded, tenant
):
    _, result = onboarded
    other_company, _ = tenant
    admin = accounting_factory.db.scalar(
        select(User).where(User.id == result["admin_user_id"])
    )

    listed = requests.get(f"{base_url}/companies?limit=500", headers=_headers(admin))

    assert listed.status_code == 200
    visible = {item["id"] for item in listed.json()["items"]}
    assert visible == {result["company_id"]}
    assert other_company.id not in visible


def test_new_client_can_immediately_reach_the_business_api(
    base_url, accounting_factory, onboarded
):
    _, result = onboarded
    admin = accounting_factory.db.scalar(
        select(User).where(User.id == result["admin_user_id"])
    )

    response = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={result['company_id']}",
        headers=_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["total"] == DEFAULT_ACCOUNT_COUNT


def test_suspending_the_new_subscription_blocks_the_business_api(
    base_url, accounting_factory, platform_admin, onboarded
):
    _, result = onboarded
    admin = accounting_factory.db.scalar(
        select(User).where(User.id == result["admin_user_id"])
    )

    suspended = requests.post(
        f"{base_url}/platform/subscriptions/{result['company_id']}/suspend",
        json={"reason": "unpaid"},
        headers=_headers(platform_admin),
    )
    assert suspended.status_code == 200

    blocked = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={result['company_id']}",
        headers=_headers(admin),
    )

    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "SUBSCRIPTION_INACTIVE"


# ── reusing an existing account ───────────────────────────────────────────────


def test_reuse_existing_user_attaches_that_account(
    base_url, accounting_factory, platform_admin
):
    existing = accounting_factory.create_user(full_name="Already Has An Account")
    accounting_factory.db.commit()

    response = requests.post(
        _url(base_url),
        json=_payload(
            accounting_factory,
            admin_email=existing.email,
            generate_password=False,
            reuse_existing_user=True,
        ),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["admin_was_existing"] is True
    assert result["admin_user_id"] == existing.id
    # No new credential exists, so none is handed over.
    assert result["generated_password"] is None
    assert "Temporary password" not in result["handover_message"]


def test_reusing_a_platform_admin_as_a_client_admin_is_refused(
    base_url, accounting_factory, platform_admin
):
    response = requests.post(
        _url(base_url),
        json=_payload(
            accounting_factory,
            admin_email=platform_admin.email,
            generate_password=False,
            reuse_existing_user=True,
        ),
        headers=_headers(platform_admin),
    )

    assert response.status_code == 409
    assert "platform administrator" in response.json()["detail"].lower()


def test_trial_onboarding_uses_the_trial_end_as_its_expiry(
    base_url, accounting_factory, platform_admin
):
    trial_ends_at = _expiry(days=14)
    body = _payload(
        accounting_factory,
        subscription_status="trial",
        trial_ends_at=trial_ends_at,
    )
    del body["subscription_expires_at"]

    response = requests.post(_url(base_url), json=body, headers=_headers(platform_admin))

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["subscription_status"] == "trial"
    assert result["effective_status"] == "trial"
    assert result["expires_at"] is not None
    assert result["days_remaining"] is not None
