import requests


FISCAL_YEAR_ID_WITH_ENTRIES = 2


def test_fiscal_year_dates_cannot_change_when_entries_exist(
    base_url,
    admin_headers,
):
    response = requests.patch(
        f"{base_url}/fiscal-years/{FISCAL_YEAR_ID_WITH_ENTRIES}",
        headers=admin_headers,
        json={
            "start_date": "2026-02-01",
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "journal entries already exist" in data["detail"]
