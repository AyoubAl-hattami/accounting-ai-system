import requests


def test_company_users_require_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_company_users_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
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
    assert len(data["items"]) > 0

    first_link = data["items"][0]

    assert "id" in first_link
    assert "company_id" in first_link
    assert "user_id" in first_link
    assert "role" in first_link
    assert "is_active" in first_link
    assert first_link["company_id"] == default_company_id


def test_company_users_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        (
            f"{base_url}/company-users"
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


def test_cannot_remove_last_admin(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    admin_user = next((u for u in data["items"] if u["role"] == "admin"), None)
    assert admin_user is not None

    company_user_id = admin_user["id"]

    # Try to demote
    patch_response = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=admin_headers,
        json={"role": "accountant"},
    )
    assert patch_response.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response.text

    # Try to remove
    patch_response_2 = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert patch_response_2.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response_2.text