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


def test_journal_entries_requires_authentication():
    response = requests.get(
        f"{BASE_URL}/journal-entries?company_id=3",
    )

    assert response.status_code in (401, 403)


def test_journal_entries_work_with_token():
    headers = login_and_get_headers()

    response = requests.get(
        f"{BASE_URL}/journal-entries?company_id=3",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    if len(data) > 0:
        first_entry = data[0]

        assert "id" in first_entry
        assert "company_id" in first_entry
        assert "entry_no" in first_entry
        assert "status" in first_entry
        assert first_entry["company_id"] == 3