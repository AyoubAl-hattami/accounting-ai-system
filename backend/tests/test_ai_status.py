import requests


def test_ai_status_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/ai/status",
    )

    assert response.status_code in (401, 403)


def test_ai_status_returns_rules_as_default(base_url, admin_headers):
    response = requests.get(
        f"{base_url}/ai/status",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["journal_provider"] == "rules"
    assert data["llm_enabled"] is False
    assert data["fallback_enabled"] is True
    assert data["source"] == "backend_rules"
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


def test_ai_status_has_all_required_fields(base_url, admin_headers):
    response = requests.get(
        f"{base_url}/ai/status",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    required_fields = [
        "journal_provider",
        "llm_enabled",
        "fallback_enabled",
        "source",
        "message",
    ]

    for field in required_fields:
        assert field in data, f"Missing field: {field}"
