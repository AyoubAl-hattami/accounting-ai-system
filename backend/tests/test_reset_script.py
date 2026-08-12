"""Contract tests for reset_company_data() — verify operational data is cleared
while structural data (accounts, fiscal config, users) is preserved."""

import sys
import os

import requests
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import reset_company_data as reset_module
from scripts.reset_company_data import reset_company_data


def test_dry_run_reports_counts_without_deleting(
    base_url, deterministic_accounting_bootstrap, accounting_factory
):
    """Dry run must return row counts and must not delete any data."""
    bs = deterministic_accounting_bootstrap
    accounting_factory.create_balanced_journal(bootstrap=bs)
    accounting_factory.db.commit()

    counts = reset_company_data(company_id=bs.company_id, confirm=False)

    assert isinstance(counts, dict)
    assert "journal_lines" in counts
    assert "journal_entries" in counts
    # Data must still be there after a dry run
    resp = requests.get(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_reset_clears_journals_but_preserves_structure(
    base_url, deterministic_accounting_bootstrap, accounting_factory
):
    """confirm=True must delete journal entries/lines but keep accounts and fiscal data."""
    bs = deterministic_accounting_bootstrap
    accounting_factory.create_balanced_journal(bootstrap=bs)
    accounting_factory.create_balanced_journal(bootstrap=bs)
    accounting_factory.db.commit()

    before = requests.get(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert before.json()["total"] >= 2

    reset_company_data(company_id=bs.company_id, confirm=True)

    after_journals = requests.get(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert after_journals.status_code == 200
    assert after_journals.json()["total"] == 0

    after_accounts = requests.get(
        f"{base_url}/accounts",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert after_accounts.status_code == 200
    assert after_accounts.json()["total"] >= 1

    after_fiscal = requests.get(
        f"{base_url}/fiscal-years",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert after_fiscal.status_code == 200
    assert after_fiscal.json()["total"] >= 1


def test_reset_cli_refuses_non_development_environment(monkeypatch):
    monkeypatch.setattr(reset_module.settings, "APP_ENV", "production")
    monkeypatch.setattr(sys, "argv", ["reset_company_data.py", "--company-id", "1"])

    with pytest.raises(SystemExit) as exc_info:
        reset_module.main()

    assert exc_info.value.code == 1
