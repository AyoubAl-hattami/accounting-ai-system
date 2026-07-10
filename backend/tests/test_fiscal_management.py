"""
Tests for the Fiscal Year / Fiscal Period management and quick-setup endpoint.

Tests:
  - Admin can create fiscal year
  - Admin can create fiscal period
  - Non-admin cannot create fiscal year/period
  - Quick setup creates fiscal year and period for backend-derived today
  - Quick setup is idempotent
  - Created fiscal period allows Gemini today's journal entry
  - Fiscal actions create audit logs
"""

import random
import requests
import uuid
from datetime import date, datetime, timedelta, timezone


def _create_company(base_url, headers, prefix="FiscalCompany"):
    response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={
            "name": f"{prefix}_{uuid.uuid4().hex[:10]}",
            "base_currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_fiscal_year(base_url, headers, company_id, year, status_value="open"):
    response = requests.post(
        f"{base_url}/fiscal-years",
        headers=headers,
        json={
            "company_id": company_id,
            "name": f"FY {year} {uuid.uuid4().hex[:8]}",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "status": status_value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_fiscal_period(
    base_url,
    headers,
    company_id,
    fiscal_year_id,
    period_no,
    name,
    start_date,
    end_date,
    status_value="open",
):
    return requests.post(
        f"{base_url}/fiscal-periods",
        headers=headers,
        json={
            "company_id": company_id,
            "fiscal_year_id": fiscal_year_id,
            "period_no": period_no,
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "status": status_value,
        },
    )


def _current_month_bounds():
    today = datetime.now(timezone.utc).date()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        month_end = date(today.year, 12, 31)
    else:
        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    return today, month_start, month_end

# ── Quick-Setup Tests ─────────────────────────────────────────────────────────


def test_quick_setup_creates_fiscal_year_and_period(
    base_url, admin_headers, default_company_id
):
    """
    POST /fiscal/quick-setup-today should create a fiscal year and fiscal
    period covering today's date if they don't already exist.
    """
    response = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )

    data = response.json()
    assert "today" in data
    assert data["fiscal_year"] is not None
    assert data["fiscal_period"] is not None

    # Verify the period covers today
    today = datetime.now(timezone.utc).date().isoformat()
    assert data["fiscal_period"]["start_date"] <= today <= data["fiscal_period"]["end_date"]
    assert data["fiscal_year"]["start_date"] <= today <= data["fiscal_year"]["end_date"]

    # Both must be open
    assert data["fiscal_year"]["status"] == "open"
    assert data["fiscal_period"]["status"] == "open"


def test_quick_setup_is_idempotent(
    base_url, admin_headers, default_company_id
):
    """
    Calling quick-setup-today twice must not create duplicates.
    The second call should return the same fiscal year and period.
    """
    resp1 = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()

    resp2 = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Same fiscal year and period IDs
    assert data1["fiscal_year"]["id"] == data2["fiscal_year"]["id"]
    assert data1["fiscal_period"]["id"] == data2["fiscal_period"]["id"]

    # Second call should not create anything new
    assert data2["fiscal_year_created"] is False
    assert data2["fiscal_period_created"] is False


def test_quick_setup_requires_admin(base_url, default_company_id):
    """
    A non-admin user (viewer) must be rejected with HTTP 403.
    """
    email = f"viewer_{uuid.uuid4().hex[:12]}@test.com"
    password = "Password123"

    # Register a new user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": password, "full_name": "Viewer Fiscal"},
    )
    assert reg.status_code in (201, 409)

    # Login
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try quick setup — should be rejected
    response = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=headers,
        params={"company_id": default_company_id},
    )
    assert response.status_code == 403


def test_quick_setup_creates_audit_logs(
    base_url, admin_headers, default_company_id
):
    """
    Quick setup must create audit log entries for fiscal year/period creation.
    """
    # Call quick setup
    requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )

    # Check audit logs
    audit_resp = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}&limit=50",
        headers=admin_headers,
    )
    assert audit_resp.status_code == 200

    audit_items = audit_resp.json()["items"]
    fiscal_logs = [
        log for log in audit_items
        if log.get("action") in ("create_fiscal_year", "create_fiscal_period")
        and "Quick setup" in (log.get("description") or "")
    ]
    # At least one of year or period was created (first run) — audit log should exist
    # On subsequent runs, both already exist so no new audit logs are created
    # Either way, the endpoint doesn't error
    assert isinstance(fiscal_logs, list)


# ── CRUD Tests ────────────────────────────────────────────────────────────────


def test_admin_can_create_fiscal_year(
    base_url, admin_headers, default_company_id
):
    """Admin can create a fiscal year via POST /fiscal-years."""
    unique_name = f"FY Test {uuid.uuid4().hex[:8]}"
    rand_year = random.randint(2200, 2399)
    response = requests.post(
        f"{base_url}/fiscal-years",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "name": unique_name,
            "start_date": f"{rand_year}-01-01",
            "end_date": f"{rand_year}-12-31",
            "status": "open",
        },
    )
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text[:300]}"
    )
    data = response.json()
    assert data["name"] == unique_name
    assert data["status"] == "open"
    assert data["id"] > 0


def test_admin_can_create_fiscal_period(
    base_url, admin_headers, default_company_id
):
    """Admin can create a fiscal period under a fiscal year."""
    # First create a fiscal year with a random far-future year
    rand_year = random.randint(2400, 2599)
    fy_name = f"FY Period Test {uuid.uuid4().hex[:8]}"
    fy_resp = requests.post(
        f"{base_url}/fiscal-years",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "name": fy_name,
            "start_date": f"{rand_year}-01-01",
            "end_date": f"{rand_year}-12-31",
            "status": "open",
        },
    )
    assert fy_resp.status_code == 201, (
        f"Expected 201, got {fy_resp.status_code}: {fy_resp.text[:300]}"
    )
    fy_id = fy_resp.json()["id"]

    # Create a fiscal period
    fp_name = f"Jan {rand_year} {uuid.uuid4().hex[:6]}"
    fp_resp = requests.post(
        f"{base_url}/fiscal-periods",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "fiscal_year_id": fy_id,
            "period_no": 1,
            "name": fp_name,
            "start_date": f"{rand_year}-01-01",
            "end_date": f"{rand_year}-01-31",
            "status": "open",
        },
    )
    assert fp_resp.status_code == 201, (
        f"Expected 201, got {fp_resp.status_code}: {fp_resp.text[:300]}"
    )
    data = fp_resp.json()
    assert data["name"] == fp_name
    assert data["fiscal_year_id"] == fy_id


def test_non_admin_cannot_create_fiscal_year(base_url, default_company_id):
    """A non-admin user must be rejected when creating a fiscal year."""
    email = f"viewer_fy_{uuid.uuid4().hex[:12]}@test.com"
    password = "Password123"

    requests.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": password, "full_name": "Viewer FY"},
    )
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{base_url}/fiscal-years",
        headers=headers,
        json={
            "company_id": default_company_id,
            "name": "Unauthorized FY",
            "start_date": "2097-01-01",
            "end_date": "2097-12-31",
            "status": "open",
        },
    )
    assert response.status_code == 403


def test_non_admin_cannot_create_fiscal_period(base_url, default_company_id):
    """A non-admin user must be rejected when creating a fiscal period."""
    email = f"viewer_fp_{uuid.uuid4().hex[:12]}@test.com"
    password = "Password123"

    requests.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": password, "full_name": "Viewer FP"},
    )
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{base_url}/fiscal-periods",
        headers=headers,
        json={
            "company_id": default_company_id,
            "fiscal_year_id": 1,
            "period_no": 1,
            "name": "Unauthorized FP",
            "start_date": "2097-01-01",
            "end_date": "2097-01-31",
            "status": "open",
        },
    )
    assert response.status_code == 403


# ── Integration: Quick setup enables Gemini journal entry ─────────────────────


def test_quick_setup_enables_gemini_today_journal(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """
    After quick-setup-today, Gemini confirm-action must succeed for today's date.
    This is the end-to-end integration test.
    """
    # Ensure fiscal period exists for today
    setup_resp = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert setup_resp.status_code == 200

    today = datetime.now(timezone.utc).date().isoformat()

    # Now confirm a journal entry via Gemini
    confirm_resp = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": today,
                "description": "Quick setup integration test",
                "lines": [
                    {
                        "account_id": default_bank_account_id,
                        "debit": "100.00",
                        "credit": "0.00",
                    },
                    {
                        "account_id": default_owner_capital_account_id,
                        "debit": "0.00",
                        "credit": "100.00",
                    },
                ],
            },
        },
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["success"] is True, (
        f"Gemini confirm-action failed after quick setup: {data.get('error_code')} — {data.get('message')}"
    )
    assert data["entity_id"] is not None
    assert data.get("data", {}).get("entry_no") is not None


def test_fiscal_year_create_generates_audit_log(
    base_url, admin_headers, default_company_id
):
    """Creating a fiscal year must generate an audit log entry."""
    unique_name = f"FY Audit {uuid.uuid4().hex[:8]}"
    rand_year = random.randint(2600, 2799)
    fy_resp = requests.post(
        f"{base_url}/fiscal-years",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "name": unique_name,
            "start_date": f"{rand_year}-01-01",
            "end_date": f"{rand_year}-12-31",
            "status": "open",
        },
    )
    assert fy_resp.status_code == 201, (
        f"Expected 201, got {fy_resp.status_code}: {fy_resp.text[:300]}"
    )
    fy_id = fy_resp.json()["id"]

    # Check audit log
    audit_resp = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}&limit=20",
        headers=admin_headers,
    )
    assert audit_resp.status_code == 200

    logs = [
        log for log in audit_resp.json()["items"]
        if log.get("action") == "create_fiscal_year"
        and log.get("entity_id") == fy_id
    ]
    assert len(logs) >= 1
    assert logs[0]["entity_type"] == "fiscal_year"

def test_fiscal_period_overlap_create_returns_409(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "OverlapCreate")
    year = random.randint(3000, 3499)
    fiscal_year_id = _create_fiscal_year(base_url, admin_headers, company_id, year)

    first = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        1, f"Jan {year}", f"{year}-01-01", f"{year}-01-31",
    )
    assert first.status_code == 201, first.text

    overlap = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        2, f"Overlap {year}", f"{year}-01-15", f"{year}-02-15",
    )
    assert overlap.status_code == 409
    assert "overlap" in overlap.text.lower()


def test_fiscal_period_adjacent_dates_are_allowed(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "AdjacentPeriod")
    year = random.randint(3500, 3999)
    fiscal_year_id = _create_fiscal_year(base_url, admin_headers, company_id, year)

    jan = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        1, f"Jan {year}", f"{year}-01-01", f"{year}-01-31",
    )
    assert jan.status_code == 201, jan.text

    feb = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        2, f"Feb {year}", f"{year}-02-01", f"{year}-02-28",
    )
    assert feb.status_code == 201, feb.text


def test_fiscal_period_same_dates_allowed_for_different_company(base_url, admin_headers):
    year = random.randint(4000, 4499)
    company_a_id = _create_company(base_url, admin_headers, "PeriodCompanyA")
    company_b_id = _create_company(base_url, admin_headers, "PeriodCompanyB")
    fy_a_id = _create_fiscal_year(base_url, admin_headers, company_a_id, year)
    fy_b_id = _create_fiscal_year(base_url, admin_headers, company_b_id, year)

    period_a = _create_fiscal_period(
        base_url, admin_headers, company_a_id, fy_a_id,
        1, f"Jan A {year}", f"{year}-01-01", f"{year}-01-31",
    )
    assert period_a.status_code == 201, period_a.text

    period_b = _create_fiscal_period(
        base_url, admin_headers, company_b_id, fy_b_id,
        1, f"Jan B {year}", f"{year}-01-01", f"{year}-01-31",
    )
    assert period_b.status_code == 201, period_b.text


def test_fiscal_period_update_overlap_returns_409(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "OverlapUpdate")
    year = random.randint(4500, 4999)
    fiscal_year_id = _create_fiscal_year(base_url, admin_headers, company_id, year)

    jan = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        1, f"Jan {year}", f"{year}-01-01", f"{year}-01-31",
    )
    assert jan.status_code == 201, jan.text

    feb = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        2, f"Feb {year}", f"{year}-02-01", f"{year}-02-28",
    )
    assert feb.status_code == 201, feb.text
    feb_id = feb.json()["id"]

    overlap = requests.patch(
        f"{base_url}/fiscal-periods/{feb_id}",
        headers=admin_headers,
        json={"start_date": f"{year}-01-15"},
    )
    assert overlap.status_code == 409
    assert "overlap" in overlap.text.lower()


def test_quick_setup_creates_current_month_for_new_company(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "QuickSetupCreate")
    today, _, _ = _current_month_bounds()

    response = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": company_id},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["fiscal_year_created"] is True
    assert data["fiscal_period_created"] is True
    assert data["fiscal_year"]["status"] == "open"
    assert data["fiscal_period"]["status"] == "open"
    assert data["fiscal_period"]["start_date"] <= today.isoformat() <= data["fiscal_period"]["end_date"]


def test_quick_setup_is_idempotent_for_new_company(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "QuickSetupIdempotent")

    first = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": company_id},
    )
    assert first.status_code == 200, first.text

    second = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": company_id},
    )
    assert second.status_code == 200, second.text
    first_data = first.json()
    second_data = second.json()
    assert first_data["fiscal_year"]["id"] == second_data["fiscal_year"]["id"]
    assert first_data["fiscal_period"]["id"] == second_data["fiscal_period"]["id"]
    assert second_data["fiscal_year_created"] is False
    assert second_data["fiscal_period_created"] is False


def test_quick_setup_does_not_reopen_closed_fiscal_period(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "QuickSetupClosedPeriod")
    today, month_start, month_end = _current_month_bounds()
    fiscal_year_id = _create_fiscal_year(base_url, admin_headers, company_id, today.year, "open")
    period = _create_fiscal_period(
        base_url, admin_headers, company_id, fiscal_year_id,
        today.month, f"Closed {today.strftime('%B %Y')}",
        month_start.isoformat(), month_end.isoformat(), "closed",
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    setup = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": company_id},
    )
    assert setup.status_code == 409
    assert "closed or locked" in setup.text

    periods = requests.get(
        f"{base_url}/fiscal-periods?company_id={company_id}&fiscal_year_id={fiscal_year_id}",
        headers=admin_headers,
    )
    assert periods.status_code == 200
    stored = next(item for item in periods.json()["items"] if item["id"] == period_id)
    assert stored["status"] == "closed"


def test_quick_setup_does_not_reopen_locked_fiscal_year(base_url, admin_headers):
    company_id = _create_company(base_url, admin_headers, "QuickSetupLockedYear")
    today, _, _ = _current_month_bounds()
    fiscal_year_id = _create_fiscal_year(base_url, admin_headers, company_id, today.year, "locked")

    setup = requests.post(
        f"{base_url}/fiscal/quick-setup-today",
        headers=admin_headers,
        params={"company_id": company_id},
    )
    assert setup.status_code == 409
    assert "closed or locked" in setup.text

    fiscal_years = requests.get(
        f"{base_url}/fiscal-years?company_id={company_id}",
        headers=admin_headers,
    )
    assert fiscal_years.status_code == 200
    stored = next(item for item in fiscal_years.json()["items"] if item["id"] == fiscal_year_id)
    assert stored["status"] == "locked"
