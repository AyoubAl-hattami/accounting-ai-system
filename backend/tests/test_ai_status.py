import requests


def test_ai_status_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/ai/status",
    )

    assert response.status_code in (401, 403)


def test_ai_status_returns_valid_provider(base_url, deterministic_accounting_bootstrap):
    dab = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/ai/status",
        headers=dab.auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    valid_providers = {"rules", "openai", "gemini", "llm_placeholder"}
    assert data["journal_provider"] in valid_providers
    assert isinstance(data["llm_enabled"], bool)
    assert data["fallback_enabled"] is True
    assert isinstance(data["source"], str)
    assert len(data["source"]) > 0
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


def test_ai_status_has_all_required_fields(base_url, deterministic_accounting_bootstrap):
    dab = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/ai/status",
        headers=dab.auth_headers,
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
