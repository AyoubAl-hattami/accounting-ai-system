"""Contract tests for scripts/onboard_client.py.

The CLI is the fallback path used when no browser is available, so it has to
produce exactly what the wizard produces: one company, one admin member, one
subscription, and an audit trail that never carries the plaintext password.
"""

import os
import sys
from uuid import uuid4

import pytest
import requests
from sqlalchemy import func, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_subscription import CompanySubscription
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.user import User
from app.core import public_url as public_url_module
from app.core.public_url import PUBLIC_URL_PLACEHOLDER
from app.modules.accounting.services.auth_service import create_user_token
from scripts.onboard_client import build_parser, run
from test_config import build_settings


MONTHS_IN_YEAR = 12
SETTLED_PASSWORD = "S3ttledCliPass"


def _run_cli(*argv: str) -> None:
    run(build_parser().parse_args(list(argv)))


def _printed_password(output: str) -> str:
    line = next(
        line for line in output.splitlines() if line.startswith("Temporary password: ")
    )
    return line.removeprefix("Temporary password: ").strip()


def _company_name() -> str:
    return f"CLI Client {uuid4().hex[:10]}"


def _admin_email() -> str:
    # A real TLD, not `.test`: the login endpoint validates the address and
    # rejects reserved special-use names.
    return f"cli-admin-{uuid4().hex[:10]}@clients-test.dev"


@pytest.fixture
def onboarded_by_cli(accounting_factory, capsys):
    """One client created through the CLI, plus what the CLI printed."""
    name, email = _company_name(), _admin_email()
    _run_cli(
        "--company-name", name,
        "--admin-email", email,
        "--admin-name", "CLI Admin",
        "--expires", "2030-12-31",
    )
    output = capsys.readouterr().out

    company = accounting_factory.db.scalar(
        select(Company).where(Company.name == name)
    )
    assert company is not None
    return company, email, output


def test_cli_creates_the_company_admin_and_subscription(
    accounting_factory, onboarded_by_cli
):
    company, email, _ = onboarded_by_cli
    db = accounting_factory.db

    admin = db.scalar(select(User).where(User.email == email))
    assert admin is not None
    assert admin.is_superuser is False

    membership = db.scalar(
        select(CompanyUser).where(
            CompanyUser.company_id == company.id, CompanyUser.user_id == admin.id
        )
    )
    assert membership is not None
    assert membership.role == "admin"

    subscription = db.scalar(
        select(CompanySubscription).where(
            CompanySubscription.company_id == company.id
        )
    )
    assert subscription is not None
    assert subscription.status == "active"


def test_cli_seeds_accounts_and_the_fiscal_calendar_by_default(
    accounting_factory, onboarded_by_cli
):
    company, _, _ = onboarded_by_cli
    db = accounting_factory.db

    accounts = db.scalar(
        select(func.count()).select_from(Account).where(Account.company_id == company.id)
    )
    periods = db.scalar(
        select(func.count())
        .select_from(FiscalPeriod)
        .where(FiscalPeriod.company_id == company.id)
    )

    assert accounts > 0
    assert periods == MONTHS_IN_YEAR


def test_cli_prints_the_handover_message_with_a_generated_password(onboarded_by_cli):
    company, email, output = onboarded_by_cli

    assert "Your accounting system access has been created." in output
    assert f"Company: {company.name}" in output
    assert f"Admin email: {email}" in output
    assert "Temporary password: " in output
    assert "Subscription valid until: 2030-12-31" in output
    # The operator has to be told the credential is spent and must be replaced.
    assert "shown once" in output
    assert "change it at first login" in output


def test_cli_prints_the_configured_public_url(accounting_factory, monkeypatch, capsys):
    monkeypatch.setattr(
        public_url_module,
        "settings",
        build_settings(APP_PUBLIC_URL="https://accounting.example.com/"),
    )

    _run_cli(
        "--company-name", _company_name(),
        "--admin-email", _admin_email(),
        "--expires", "2030-12-31",
    )
    output = capsys.readouterr().out

    assert "Login URL         https://accounting.example.com" in output
    assert "Login URL: https://accounting.example.com" in output
    assert PUBLIC_URL_PLACEHOLDER not in output


def test_cli_warns_when_no_public_url_is_configured(
    accounting_factory, monkeypatch, capsys
):
    monkeypatch.setattr(public_url_module, "settings", build_settings(APP_PUBLIC_URL=""))

    _run_cli(
        "--company-name", _company_name(),
        "--admin-email", _admin_email(),
        "--expires", "2030-12-31",
    )
    output = capsys.readouterr().out

    assert "APP_PUBLIC_URL is not set" in output
    assert f"Login URL: {PUBLIC_URL_PLACEHOLDER}" in output


def test_cli_audit_log_omits_the_generated_password(
    accounting_factory, onboarded_by_cli
):
    company, _, output = onboarded_by_cli
    db = accounting_factory.db

    # Recover the one password the CLI printed, so the assertion checks the real
    # secret rather than a plausible-looking stand-in.
    password = _printed_password(output)
    assert password

    log = db.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "client_onboarding",
            AuditLog.entity_id == company.id,
        )
    )
    assert log is not None
    assert log.action == "onboard_client"
    assert password not in str(log.new_values)
    assert password not in (log.description or "")


def test_cli_created_admin_is_locked_to_the_password_change(
    base_url, accounting_factory, onboarded_by_cli
):
    """The CLI hands over a password too, so it earns the same lock."""
    _, email, _ = onboarded_by_cli
    admin = accounting_factory.db.scalar(select(User).where(User.email == email))

    blocked = requests.get(
        f"{base_url}/companies",
        headers={"Authorization": f"Bearer {create_user_token(admin)}"},
    )

    assert admin.must_change_password is True
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_cli_created_admin_reaches_only_its_company_once_settled(
    base_url, accounting_factory, onboarded_by_cli
):
    company, email, output = onboarded_by_cli
    temporary = _printed_password(output)

    login = requests.post(
        f"{base_url}/auth/login", json={"email": email, "password": temporary}
    )
    assert login.status_code == 200, login.text
    changed = requests.post(
        f"{base_url}/auth/change-temporary-password",
        json={
            "current_password": temporary,
            "new_password": SETTLED_PASSWORD,
            "confirm_password": SETTLED_PASSWORD,
        },
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert changed.status_code == 200, changed.text

    accounting_factory.db.expire_all()
    admin = accounting_factory.db.scalar(select(User).where(User.email == email))
    response = requests.get(
        f"{base_url}/companies",
        headers={"Authorization": f"Bearer {create_user_token(admin)}"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [company.id]


def test_cli_refuses_a_duplicate_company_name(accounting_factory, onboarded_by_cli):
    company, _, _ = onboarded_by_cli

    with pytest.raises(SystemExit) as exit_info:
        _run_cli(
            "--company-name", company.name,
            "--admin-email", _admin_email(),
            "--expires", "2030-12-31",
        )

    assert exit_info.value.code == 1


def test_cli_requires_a_subscription_window(accounting_factory):
    with pytest.raises(SystemExit) as exit_info:
        _run_cli("--company-name", _company_name(), "--admin-email", _admin_email())

    assert exit_info.value.code == 1


def test_cli_refuses_a_password_and_a_generate_flag_together(accounting_factory):
    with pytest.raises(SystemExit) as exit_info:
        _run_cli(
            "--company-name", _company_name(),
            "--admin-email", _admin_email(),
            "--expires", "2030-12-31",
            "--password", "Str0ngHandover",
            "--generate-password",
        )

    assert exit_info.value.code == 1


def test_cli_can_skip_the_optional_accounting_setup(accounting_factory):
    name = _company_name()
    _run_cli(
        "--company-name", name,
        "--admin-email", _admin_email(),
        "--expires", "2030-12-31",
        "--no-seed-accounts",
        "--no-fiscal-year",
    )

    db = accounting_factory.db
    company = db.scalar(select(Company).where(Company.name == name))
    accounts = db.scalar(
        select(func.count()).select_from(Account).where(Account.company_id == company.id)
    )
    periods = db.scalar(
        select(func.count())
        .select_from(FiscalPeriod)
        .where(FiscalPeriod.company_id == company.id)
    )

    assert accounts == 0
    assert periods == 0
