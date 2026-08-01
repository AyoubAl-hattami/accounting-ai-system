"""Auth and pagination contract tests for the /audit-logs endpoint."""
import requests


def test_audit_logs_require_authentication(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(f"{base_url}/audit-logs?company_id={bs.company_id}")
    assert response.status_code in (401, 403)


def test_audit_logs_work_with_token(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])

    for log in data["items"]:
        assert "id" in log
        assert "company_id" in log
        assert "action" in log
        assert "entity_type" in log
        assert log["company_id"] == bs.company_id


def test_audit_logs_pagination_metadata(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}&skip=0&limit=5",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5


def test_audit_logs_action_filter(base_url, deterministic_accounting_bootstrap):
    """Action filter query param is accepted and only matching logs are returned."""
    bs = deterministic_accounting_bootstrap

    all_response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}&limit=100",
        headers=bs.auth_headers,
    )
    assert all_response.status_code == 200
    items = all_response.json().get("items", [])

    if not items:
        response = requests.get(
            f"{base_url}/audit-logs?company_id={bs.company_id}&action=login_success",
            headers=bs.auth_headers,
        )
        assert response.status_code == 200
        return

    known_action = items[0]["action"]
    response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}&action={known_action}",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    for item in data["items"]:
        assert item["action"] == known_action


def test_audit_logs_action_filter_unknown_action_returns_empty(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}"
        f"&action=this_action_does_not_exist_xyz",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
