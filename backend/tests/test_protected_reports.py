import requests


def test_trial_balance_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/trial-balance?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_trial_balance_works_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/reports/trial-balance?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == default_company_id
    assert "total_debit" in data
    assert "total_credit" in data
    assert "is_balanced" in data