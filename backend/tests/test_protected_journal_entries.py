import requests


def test_journal_entries_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_journal_entries_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}",
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
        first_entry = data["items"][0]

        assert "id" in first_entry
        assert "company_id" in first_entry
        assert "entry_no" in first_entry
        assert "status" in first_entry
        assert first_entry["company_id"] == default_company_id


def test_journal_entries_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        (
            f"{base_url}/journal-entries"
            f"?company_id={default_company_id}&skip=0&limit=5"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5