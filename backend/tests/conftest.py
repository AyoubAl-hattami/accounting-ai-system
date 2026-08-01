import os
import pytest

from app.core.database import SessionLocal
from app.core.rate_limit import _attempts, _lock
from app.modules.accounting.services.auth_service import create_user_token
from factories.accounting import AccountingTestFactory


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear in-memory rate-limit state before every test to prevent cross-test pollution."""
    with _lock:
        _attempts.clear()
    yield
    with _lock:
        _attempts.clear()


@pytest.fixture
def base_url():
    return BASE_URL


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


@pytest.fixture
def deterministic_superuser(accounting_factory):
    """Factory-created platform superuser (committed, ready for HTTP use)."""
    user = accounting_factory.create_superuser()
    accounting_factory.db.commit()
    yield user


@pytest.fixture
def deterministic_superuser_headers(accounting_factory):
    """Auth headers for a factory-created platform superuser."""
    user = accounting_factory.create_superuser()
    accounting_factory.db.commit()
    headers = {"Authorization": f"Bearer {create_user_token(user)}"}
    yield headers
