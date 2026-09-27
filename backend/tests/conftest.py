import os
import urllib.error
import urllib.request

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.accounting.services.auth_service import create_user_token
from factories.accounting import AccountingTestFactory


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")

COMPOSE_FILE = "docker-compose.test.yml"

# Fixtures that cannot work without the disposable stack.  `item.fixturenames`
# is the transitive closure, so naming the two roots also covers
# deterministic_accounting_bootstrap, deterministic_superuser and
# deterministic_superuser_headers, which all build on accounting_factory.
_API_FIXTURE = "base_url"
_DATABASE_FIXTURE = "accounting_factory"

# Fixtures alone are not enough to spot a test that needs the stack: 38 of the
# 39 HTTP files take `base_url`, but test_health.py imports requests and calls a
# hardcoded URL with no fixture at all.  Checking the module for the imported
# name catches that one and anything written the same way later, and matches how
# fixture_readiness.py already classifies these files.
_API_MODULE_IMPORT = "requests"
_DATABASE_MODULE_IMPORT = "SessionLocal"


def _item_needs(item, fixture_name: str, module_import: str) -> bool:
    if fixture_name in getattr(item, "fixturenames", ()):
        return True
    module = getattr(item, "module", None)
    return module is not None and hasattr(module, module_import)


def _startup_instructions() -> str:
    return (
        f"\n    docker compose -f {COMPOSE_FILE} up -d --wait\n\n"
        "then, from backend/:\n\n"
        "    APP_ENV=test \\\n"
        "    SECRET_KEY=local-test-secret-key-not-for-production-abcdef \\\n"
        "    DATABASE_URL=postgresql+psycopg2://postgres:postgres"
        "@127.0.0.1:55432/accounting_ai \\\n"
        "    ACCOUNTING_TEST_BASE_URL=http://127.0.0.1:8010 \\\n"
        "    python -m pytest\n"
    )


def _api_failure() -> str | None:
    """Return a description of why the API is unusable, or None if it is fine."""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/db", timeout=5) as response:
            if response.status != 200:
                return f"{BASE_URL}/health/db answered HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        # Reachable but unhealthy -- almost always the API is up while its
        # database is not, which /health/db is precisely there to surface.
        return f"{BASE_URL}/health/db answered HTTP {exc.code}"
    except Exception as exc:
        return f"{BASE_URL} is unreachable ({type(exc).__name__})"
    return None


def _database_failure() -> str | None:
    """Return a description of why the database is unusable, or None if fine."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        return (
            f"DATABASE_URL is unreachable from this process ({type(exc).__name__}). "
            "Note the suite connects from the host, not from inside the compose "
            "network, so the database must be published on 127.0.0.1:55432."
        )
    return None


def pytest_collection_modifyitems(session, config, items):
    """Fail fast, once, when the collected tests need a stack that is not up.

    Deliberately not an autouse fixture.  48 of the 87 test files need neither
    the API nor the database, and a blanket gate would abort those too; the
    whole suite currently yields 583 passes with no infrastructure at all.  This
    probes only when something that actually needs the stack was collected, so
    `pytest tests/test_architecture_guards.py` still runs on a bare checkout.

    Without this, a clean checkout spends four and a half minutes producing 53
    failures and 293 errors, every one of them a bare ConnectionError that says
    nothing about what to start.
    """
    needs_api = any(
        _item_needs(item, _API_FIXTURE, _API_MODULE_IMPORT) for item in items
    )
    needs_database = any(
        _item_needs(item, _DATABASE_FIXTURE, _DATABASE_MODULE_IMPORT) for item in items
    )

    problems = []
    if needs_api:
        problems.append(_api_failure())
    if needs_database:
        problems.append(_database_failure())
    problems = [problem for problem in problems if problem]

    if not problems:
        return

    detail = "\n".join(f"  - {problem}" for problem in problems)
    pytest.exit(
        "\n"
        "The collected tests need the disposable test stack, which is not up.\n\n"
        f"{detail}\n\n"
        f"Start it with:\n{_startup_instructions()}\n"
        f"Currently: ACCOUNTING_TEST_BASE_URL={BASE_URL}\n"
        f"           DATABASE_URL={settings.DATABASE_URL.split('@')[-1]}\n\n"
        "To run only the tests that need no stack, select them by path, for\n"
        "example: python -m pytest tests/test_architecture_guards.py\n",
        returncode=1,
    )


# There is deliberately no rate-limiter reset fixture here.
#
# There used to be one, clearing app.core.rate_limit._attempts around every
# test.  It never isolated anything.  The limiter it cleared lived in THIS
# process, while the limiter under test lives in the server process the suite
# talks to over HTTP -- clearing a dict here could not reach it.  The counters
# now live in the rate_limit_attempts table, which makes that plainer but did
# not change it.
#
# Nothing needed it.  test_auth_rate_limit.py -- the only test that exercises
# the limiter -- builds a fresh uuid4 email per run, so its bucket key
# ("login:{ip}:{email}") is unique by construction and no previous test can
# have touched it.  That is the isolation, and it is the isolation that was
# actually working.
#
# If a future test needs a bucket cleared for real, call
# rate_limit.reset_attempts(key), which deletes the rows. Do not reintroduce an
# autouse fixture: it would run against all 552 offline tests, which have no
# database to delete from.


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
