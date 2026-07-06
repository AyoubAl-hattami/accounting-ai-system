import requests


def test_audit_logs_require_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_audit_logs_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data

    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])

    if len(data["items"]) > 0:
        first_log = data["items"][0]

        assert "id" in first_log
        assert "company_id" in first_log
        assert "action" in first_log
        assert "entity_type" in first_log
        assert first_log["company_id"] == default_company_id


def test_audit_logs_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}&skip=0&limit=5",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5


def test_audit_logs_action_filter(
    base_url,
    admin_headers,
    default_company_id,
):
    """
    Action filter query param is accepted and only matching logs are returned.
    We first fetch all logs, pick the first action that appears, then verify
    the filter narrows results to only that action.
    """
    # Fetch all logs (up to limit) to find a real action value
    all_response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}&limit=100",
        headers=admin_headers,
    )
    assert all_response.status_code == 200
    all_data = all_response.json()

    items = all_data.get("items", [])

    if not items:
        # No logs yet - just confirm the filter param is accepted with 200
        response = requests.get(
            f"{base_url}/audit-logs?company_id={default_company_id}"
            f"&action=login_success",
            headers=admin_headers,
        )
        assert response.status_code == 200
        return

    # Use the first available action as the filter
    known_action = items[0]["action"]

    response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}"
        f"&action={known_action}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data

    # All returned items must match the filtered action
    for item in data["items"]:
        assert item["action"] == known_action


def test_audit_logs_action_filter_unknown_action_returns_empty(
    base_url,
    admin_headers,
    default_company_id,
):
    """Filtering by a nonexistent action should return an empty result set."""
    response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}"
        f"&action=this_action_does_not_exist_xyz",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
