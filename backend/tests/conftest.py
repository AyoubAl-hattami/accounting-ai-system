import os
import requests
import pytest


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Password123"
DEFAULT_COMPANY_ID = 3
DEFAULT_BANK_ACCOUNT_ID = 5
DEFAULT_OWNER_CAPITAL_ACCOUNT_ID = 11


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def default_company_id():
    return DEFAULT_COMPANY_ID


@pytest.fixture
def default_bank_account_id():
    return DEFAULT_BANK_ACCOUNT_ID


@pytest.fixture
def default_owner_capital_account_id():
    return DEFAULT_OWNER_CAPITAL_ACCOUNT_ID


@pytest.fixture
def admin_headers():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }