import uuid

import requests


def test_failed_login_rate_limit(base_url):
    email = f"rate_limit_{uuid.uuid4().hex}@example.com"
    wrong_password = "WrongPassword999"

    for i in range(5):
        response = requests.post(
            f"{base_url}/auth/login",
            json={
                "email": email,
                "password": wrong_password,
            },
        )

        assert response.status_code == 401, (
            f"Attempt {i + 1}: expected 401, got {response.status_code}"
        )

    response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": email,
            "password": wrong_password,
        },
    )

    assert response.status_code == 429

    data = response.json()

    assert "Too many failed login attempts" in data["detail"]
