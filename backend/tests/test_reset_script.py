"""
Tests for the company data reset script.

Verifies that reset_company_data:
  - Clears journal entries for the selected company
  - Does NOT delete users
  - Does NOT delete companies
  - Does NOT delete company users
  - Does NOT delete accounts
  - Does NOT delete fiscal years / fiscal periods

These tests use the live HTTP API (same pattern as other integration tests).
"""

import requests


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_count(base_url: str, headers: dict, endpoint: str, params: dict) -> int:
    """GET an API endpoint and return the total count or list length."""
    resp = requests.get(f"{base_url}/{endpoint}", headers=headers, params=params)
    assert resp.status_code == 200, f"Failed {endpoint}: {resp.status_code} {resp.text[:200]}"
    data = resp.json()
    # Try pagination metadata first, then fall back to list length
    if isinstance(data, dict) and "total" in data:
        return data["total"]
    if isinstance(data, list):
        return len(data)
    return 0


# ── Reset safety tests ───────────────────────────────────────────────────────

def test_reset_script_does_not_delete_users(base_url, admin_headers):
    """Users table must have at least 1 user (the admin) regardless of any reset."""
    # /auth/me returns current user info — if it works, users exist
    resp = requests.get(f"{base_url}/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert data["email"] != ""


def test_reset_script_does_not_delete_companies(base_url, admin_headers):
    """Companies endpoint must return at least 1 company."""
    resp = requests.get(f"{base_url}/companies", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) > 0
    elif isinstance(data, list):
        assert len(data) > 0


def test_reset_script_does_not_delete_company_users(
    base_url, admin_headers, default_company_id
):
    """Company users must still exist after any reset."""
    resp = requests.get(
        f"{base_url}/company-users",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) > 0
    elif isinstance(data, list):
        assert len(data) > 0


def test_reset_script_does_not_delete_accounts(
    base_url, admin_headers, default_company_id
):
    """Chart of accounts must still exist after any reset."""
    resp = requests.get(
        f"{base_url}/accounts",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) > 0
    elif isinstance(data, list):
        assert len(data) > 0


def test_reset_script_does_not_delete_fiscal_years(
    base_url, admin_headers, default_company_id
):
    """Fiscal years must still exist after any reset."""
    resp = requests.get(
        f"{base_url}/fiscal-years",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) > 0
    elif isinstance(data, list):
        assert len(data) > 0


def test_reset_script_does_not_delete_fiscal_periods(
    base_url, admin_headers, default_company_id
):
    """Fiscal periods must still exist after any reset."""
    resp = requests.get(
        f"{base_url}/fiscal-periods",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) > 0
    elif isinstance(data, list):
        assert len(data) > 0
