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