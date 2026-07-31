import os
import uuid
import requests
import pytest

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token
from factories.accounting import AccountingTestFactory


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


@pytest.fixture
def superuser_headers():
    email = f"platform_superuser_{uuid.uuid4().hex}@example.com"
    with SessionLocal() as db:
        user = User(
            email=email,
            full_name="Platform Superuser Test",
            hashed_password=hash_password("Password123"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_user_token(user)

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture
def accounting_factory():
    with SessionLocal() as db:
        factory = AccountingTestFactory(db)
        yield factory
        db.rollback()


@pytest.fixture
def deterministic_accounting_bootstrap(accounting_factory):
    bootstrap = accounting_factory.create_accounting_bootstrap()
    accounting_factory.db.commit()
    return bootstrap
