import requests


BASE_URL = "http://127.0.0.1:8010"


def login_and_get_headers():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_fiscal_years_require_authentication():
    response = requests.get(
        f"{BASE_URL}/fiscal-years?company_id=3",
    )

    assert response.status_code in (401, 403)


def test_fiscal_years_work_with_token():
    headers = login_and_get_headers()

    response = requests.get(
        f"{BASE_URL}/fiscal-years?company_id=3",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    if len(data) > 0:
        first_year = data[0]

        assert "id" in first_year
        assert "company_id" in first_year
        assert "name" in first_year
        assert "status" in first_year
        assert first_year["company_id"] == 3


def test_fiscal_periods_require_authentication():
    response = requests.get(
        f"{BASE_URL}/fiscal-periods?company_id=3",
    )

    assert response.status_code in (401, 403)


def test_fiscal_periods_work_with_token():
    headers = login_and_get_headers()

    response = requests.get(
        f"{BASE_URL}/fiscal-periods?company_id=3",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    if len(data) > 0:
        first_period = data[0]

        assert "id" in first_period
        assert "company_id" in first_period
        assert "fiscal_year_id" in first_period
        assert "period_no" in first_period
        assert "status" in first_period
        assert first_period["company_id"] == 3