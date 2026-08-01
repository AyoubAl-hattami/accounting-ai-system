"""Auth and pagination contract tests for the /companies endpoint."""
import requests


def test_companies_require_authentication(base_url):
    response = requests.get(f"{base_url}/companies")
    assert response.status_code in (401, 403)


def test_companies_work_with_token_and_pagination(
    base_url, deterministic_superuser_headers
):
    response = requests.get(
        f"{base_url}/companies?skip=0&limit=5",
        headers=deterministic_superuser_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5

    if data["items"]:
        first_company = data["items"][0]
        assert "id" in first_company
        assert "name" in first_company
        assert "base_currency" in first_company
