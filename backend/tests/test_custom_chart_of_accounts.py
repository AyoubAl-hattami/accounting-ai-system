"""A company's chart is its own: custom names, optional starter templates, no forced structure."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import requests
from sqlalchemy import select

from app.application.accounts.defaults import (
    CHART_TEMPLATES,
    DEFAULT_ACCOUNTS,
    resolve_chart_template,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
from app.modules.accounting.services.account_mapper import map_to_accounts
from app.modules.accounting.services.auth_service import create_user_token


ONBOARDING_ENDPOINT = "/platform/onboarding/clients"
ONBOARDING_DEFAULTS_ENDPOINT = "/platform/onboarding/defaults"


def _headers(user):
    return {"Authorization": f"Bearer {create_user_token(user)}"}


@pytest.fixture
def platform_admin(accounting_factory):
    user = accounting_factory.create_superuser()
    accounting_factory.db.commit()
    return user


def _onboarding_payload(factory, **overrides) -> dict:
    body = {
        "company_name": f"Chart Co {uuid4().hex[:10]}",
        "base_currency": "YER",
        "admin_email": factory.unique_email("chart-admin"),
        "admin_full_name": "Chart Admin",
        "generate_password": True,
        "plan_code": "monthly",
        "subscription_status": "trial",
        "subscription_expires_at": (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).isoformat(),
    }
    body.update(overrides)
    return body


def _company_accounts(company_id: int, db) -> list[Account]:
    return list(
        db.scalars(select(Account).where(Account.company_id == company_id))
    )


# ── custom accounts ───────────────────────────────────────────────────────────


def test_company_can_create_accounts_named_for_its_own_country(
    base_url, deterministic_accounting_bootstrap
):
    """"الكريمي" and "Jawali Wallet" are ordinary accounts, not special cases."""
    bs = deterministic_accounting_bootstrap
    created = []
    for name, subtype in (
        ("الكريمي", "bank"),
        ("Jawali Wallet", "e_wallet"),
        ("صندوق نقدي", "cash"),
    ):
        response = requests.post(
            f"{base_url}/accounts",
            headers=bs.auth_headers,
            json={
                "company_id": bs.company_id,
                "code": uuid4().hex[:12],
                "name": name,
                "account_type": "asset",
                "account_subtype": subtype,
                "parent_id": None,
                "description": None,
                "is_active": True,
            },
        )
        assert response.status_code == 201, response.text
        account = response.json()
        assert account["name"] == name
        assert account["account_subtype"] == subtype
        assert account["is_system"] is False
        created.append(account)

    trial_balance = requests.get(
        f"{base_url}/reports/trial-balance",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert trial_balance.status_code == 200, trial_balance.text
    reported = {line["account_id"]: line for line in trial_balance.json()["lines"]}
    for account in created:
        # Reports read account_type; the name and the subtype are decoration.
        assert reported[account["id"]]["account_type"] == "asset"


def test_subtype_is_optional_and_reclassifiable_after_seeding(
    base_url, deterministic_accounting_bootstrap
):
    """Existing accounts start unclassified and can be labelled later."""
    bs = deterministic_accounting_bootstrap
    response = requests.post(
        f"{base_url}/accounts",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "code": uuid4().hex[:12],
            "name": "Unclassified holding",
            "account_type": "asset",
            "parent_id": None,
            "description": None,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    account = response.json()
    assert account["account_subtype"] is None

    patched = requests.patch(
        f"{base_url}/accounts/{account['id']}",
        headers=bs.auth_headers,
        json={"account_subtype": "e_wallet"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["account_subtype"] == "e_wallet"
    assert patched.json()["account_type"] == "asset"


def test_subtype_lets_the_assistant_find_a_locally_named_payment_account():
    """A "bank" hint must reach an account nobody would recognise by name."""
    accounts = [
        {
            "id": 1,
            "code": "1110",
            "name": "الكريمي",
            "account_type": "asset",
            "account_subtype": "bank",
            "is_active": True,
        },
        {
            "id": 2,
            "code": "5100",
            "name": "Rent Expense",
            "account_type": "expense",
            "account_subtype": "expense",
            "is_active": True,
        },
    ]

    mapped = map_to_accounts(
        ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=300.0,
            description="paid rent from the bank",
            debit_account_hint="rent expense",
            payment_source_hint="bank",
            confidence=0.8,
        ),
        accounts,
        language="en",
    )

    assert mapped.needs_clarification is False, mapped.clarification_question
    assert mapped.debit_account_id == 2
    assert mapped.credit_account_id == 1


# ── starter templates ─────────────────────────────────────────────────────────


def test_regional_template_is_opt_in_and_fully_editable():
    """Yemen is one choice among many, and its payment accounts are not locked."""
    assert resolve_chart_template(None) == DEFAULT_ACCOUNTS
    assert resolve_chart_template("default") == DEFAULT_ACCOUNTS
    assert resolve_chart_template("not-a-template") == DEFAULT_ACCOUNTS
    assert "yemen_cash_wallet" in CHART_TEMPLATES

    yemen = resolve_chart_template("yemen_cash_wallet")
    assert yemen != DEFAULT_ACCOUNTS

    subtypes = {definition.account_subtype for definition in yemen}
    assert {"cash", "bank", "e_wallet"} <= subtypes

    # Structural parents keep the reports' spine; every leaf stays the client's.
    payment_accounts = [
        definition
        for definition in yemen
        if definition.account_subtype in {"cash", "bank", "e_wallet"}
    ]
    assert payment_accounts
    assert all(not definition.is_system for definition in payment_accounts)


def test_onboarding_can_seed_default_blank_or_regional_charts(
    base_url, accounting_factory, platform_admin
):
    """The platform owner picks the starting point; blank means genuinely blank."""
    outcomes = {}
    for setup, overrides in (
        ("default", {"seed_default_accounts": True, "chart_template": "default"}),
        ("blank", {"seed_default_accounts": False}),
        (
            "yemen",
            {"seed_default_accounts": True, "chart_template": "yemen_cash_wallet"},
        ),
    ):
        response = requests.post(
            f"{base_url}{ONBOARDING_ENDPOINT}",
            headers=_headers(platform_admin),
            json=_onboarding_payload(accounting_factory, **overrides),
        )
        assert response.status_code == 201, response.text
        outcomes[setup] = response.json()

    assert outcomes["blank"]["seeded_accounts_count"] == 0
    assert outcomes["default"]["seeded_accounts_count"] == len(DEFAULT_ACCOUNTS)
    assert outcomes["yemen"]["seeded_accounts_count"] == len(
        resolve_chart_template("yemen_cash_wallet")
    )

    accounting_factory.db.expire_all()
    assert _company_accounts(outcomes["blank"]["company_id"], accounting_factory.db) == []

    yemen_accounts = _company_accounts(
        outcomes["yemen"]["company_id"], accounting_factory.db
    )
    assert {"cash", "bank", "e_wallet"} <= {
        account.account_subtype for account in yemen_accounts
    }
    assert any(not account.is_system for account in yemen_accounts)


def test_onboarding_defaults_advertise_the_generic_chart(
    base_url, platform_admin
):
    """No country may be the default starting point."""
    response = requests.get(
        f"{base_url}{ONBOARDING_DEFAULTS_ENDPOINT}",
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200, response.text
    defaults = response.json()
    assert defaults["default_chart_template"] == "default"
    assert "yemen_cash_wallet" in defaults["chart_templates"]


def test_unknown_chart_template_is_rejected_not_guessed(
    base_url, accounting_factory, platform_admin
):
    response = requests.post(
        f"{base_url}{ONBOARDING_ENDPOINT}",
        headers=_headers(platform_admin),
        json=_onboarding_payload(accounting_factory, chart_template="atlantis"),
    )

    assert response.status_code == 422, response.text
