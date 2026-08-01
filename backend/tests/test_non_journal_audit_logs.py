"""Audit log tests for non-journal actions (company, account, register)."""
import uuid

import requests


# All tests that create companies require a platform superuser.  The
# deterministic_superuser_headers fixture provides that without touching
# admin@example.com or any seeded company.


def test_register_creates_audit_log(base_url):
    """User registration creates a user; audit log is company_id=None (not queryable here)."""
    unique_email = f"audit_reg_{uuid.uuid4().hex[:12]}@accounting-ai-test.dev"
    register_response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": unique_email,
            "password": "Password123",
            "full_name": "Audit Register Test",
        },
    )
    assert register_response.status_code == 201
    new_user = register_response.json()
    assert new_user["id"] is not None
    assert new_user["is_active"] is True


def test_create_company_creates_audit_log(base_url, deterministic_superuser_headers):
    headers = deterministic_superuser_headers
    unique_name = f"AuditTestCo_{uuid.uuid4().hex[:10]}"

    create_response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={"name": unique_name, "base_currency": "USD"},
    )
    assert create_response.status_code == 201
    company = create_response.json()
    company_id = company["id"]
    assert company["name"] == unique_name

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={company_id}",
        headers=headers,
    )
    assert audit_response.status_code == 200
    audit_data = audit_response.json()
    actions = [log["action"] for log in audit_data["items"]]
    assert "create_company" in actions

    create_log = next(
        log for log in audit_data["items"] if log["action"] == "create_company"
    )
    assert create_log["entity_type"] == "company"
    assert create_log["entity_id"] == company_id
    assert create_log["company_id"] == company_id


def test_seed_default_accounts_creates_audit_log(
    base_url, deterministic_superuser_headers
):
    headers = deterministic_superuser_headers
    unique_name = f"SeedAuditCo_{uuid.uuid4().hex[:10]}"

    create_response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={"name": unique_name, "base_currency": "USD"},
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    seed_response = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={company_id}",
        headers=headers,
    )
    assert seed_response.status_code == 200
    seed_data = seed_response.json()
    assert seed_data["created_count"] > 0

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={company_id}",
        headers=headers,
    )
    assert audit_response.status_code == 200
    audit_data = audit_response.json()
    actions = [log["action"] for log in audit_data["items"]]
    assert "seed_default_accounts" in actions

    seed_log = next(
        log for log in audit_data["items"] if log["action"] == "seed_default_accounts"
    )
    assert seed_log["entity_type"] == "account"
    assert seed_log["company_id"] == company_id
    assert seed_log["entity_id"] is None
    assert seed_log["description"] == (
        f"Seeded default accounts: {seed_data['created_count']} created, "
        f"{seed_data['skipped_count']} skipped"
    )


def test_update_company_creates_audit_log(base_url, deterministic_superuser_headers):
    headers = deterministic_superuser_headers
    unique_name = f"UpdAuditCo_{uuid.uuid4().hex[:10]}"

    create_response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={"name": unique_name, "base_currency": "USD"},
    )
    assert create_response.status_code == 201
    company_id = create_response.json()["id"]

    update_response = requests.patch(
        f"{base_url}/companies/{company_id}",
        headers=headers,
        json={"name": f"{unique_name}_updated"},
    )
    assert update_response.status_code == 200

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={company_id}",
        headers=headers,
    )
    assert audit_response.status_code == 200
    audit_data = audit_response.json()
    actions = [log["action"] for log in audit_data["items"]]
    assert "update_company" in actions

    update_log = next(
        log for log in audit_data["items"] if log["action"] == "update_company"
    )
    assert update_log["entity_type"] == "company"
    assert update_log["entity_id"] == company_id
    assert update_log["company_id"] == company_id


def test_create_account_creates_exactly_one_audit_log(
    base_url, deterministic_superuser_headers
):
    headers = deterministic_superuser_headers
    create_company_response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={
            "name": f"AccountAuditCo_{uuid.uuid4().hex[:8]}",
            "base_currency": "USD",
        },
    )
    assert create_company_response.status_code == 201
    company_id = create_company_response.json()["id"]

    create_account_response = requests.post(
        f"{base_url}/accounts",
        headers=headers,
        json={
            "company_id": company_id,
            "code": uuid.uuid4().hex[:12],
            "name": "Audit account",
            "account_type": "asset",
            "parent_id": None,
            "description": None,
            "is_active": True,
            "is_system": False,
        },
    )
    assert create_account_response.status_code == 201
    account = create_account_response.json()

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={company_id}&action=create_account",
        headers=headers,
    )
    assert audit_response.status_code == 200
    matching_logs = [
        log
        for log in audit_response.json()["items"]
        if log["entity_type"] == "account" and log["entity_id"] == account["id"]
    ]
    assert len(matching_logs) == 1
    assert matching_logs[0]["company_id"] == company_id
    assert matching_logs[0]["description"] == (
        f"Created account {account['code']} - {account['name']}"
    )


def test_update_account_creates_exactly_one_audit_log_with_before_and_after_values(
    base_url, deterministic_superuser_headers
):
    headers = deterministic_superuser_headers
    company_response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={
            "name": f"AccountUpdateAuditCo_{uuid.uuid4().hex[:8]}",
            "base_currency": "USD",
        },
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    account_response = requests.post(
        f"{base_url}/accounts",
        headers=headers,
        json={
            "company_id": company_id,
            "code": uuid.uuid4().hex[:12],
            "name": "Before audit",
            "account_type": "asset",
            "parent_id": None,
            "description": None,
            "is_active": True,
            "is_system": False,
        },
    )
    assert account_response.status_code == 201
    before = account_response.json()

    update_response = requests.patch(
        f"{base_url}/accounts/{before['id']}",
        headers=headers,
        json={"name": "After audit", "is_active": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={company_id}&action=update_account",
        headers=headers,
    )
    assert audit_response.status_code == 200
    matching = [
        log
        for log in audit_response.json()["items"]
        if log["entity_type"] == "account" and log["entity_id"] == before["id"]
    ]
    assert len(matching) == 1
    log = matching[0]
    assert log["action"] == "update_account"
    assert log["company_id"] == company_id
    assert log["description"] == (
        f"Updated account {updated['code']} - {updated['name']}"
    )
    assert log["old_values"] == {
        "name": before["name"],
        "code": before["code"],
        "is_active": before["is_active"],
    }
    assert log["new_values"] == {
        "name": updated["name"],
        "code": updated["code"],
        "is_active": updated["is_active"],
    }
    assert log["actor_email"] is not None
