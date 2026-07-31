import requests


def test_trial_balance_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/trial-balance?company_id=1",
    )

    assert response.status_code in (401, 403)


def test_trial_balance_works_with_token(
    base_url,
    deterministic_accounting_bootstrap,
):
    company_id = deterministic_accounting_bootstrap.company_id
    response = requests.get(
        f"{base_url}/reports/trial-balance?company_id={company_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == company_id
    assert "total_debit" in data
    assert "total_credit" in data
    assert "is_balanced" in data
