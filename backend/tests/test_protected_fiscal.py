import requests


def test_fiscal_years_require_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/fiscal-years?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_fiscal_years_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/fiscal-years?company_id={default_company_id}",
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
        first_year = data["items"][0]

        assert "id" in first_year
        assert "company_id" in first_year
        assert "name" in first_year
        assert "status" in first_year
        assert first_year["company_id"] == default_company_id


def test_fiscal_years_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/fiscal-years?company_id={default_company_id}&skip=0&limit=5",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5


def test_fiscal_periods_require_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/fiscal-periods?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_fiscal_periods_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/fiscal-periods?company_id={default_company_id}",
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
        first_period = data["items"][0]

        assert "id" in first_period
        assert "company_id" in first_period
        assert "fiscal_year_id" in first_period
        assert "period_no" in first_period
        assert "status" in first_period
        assert first_period["company_id"] == default_company_id


def test_fiscal_periods_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/fiscal-periods?company_id={default_company_id}&skip=0&limit=5",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5