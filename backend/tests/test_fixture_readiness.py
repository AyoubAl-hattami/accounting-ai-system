"""Guards for the documented full-suite fixture migration blockers."""

from fixture_readiness import (
    BACKEND_ROOT,
    EXPECTED_DIRECT_SESSION_FILES,
    EXPECTED_FACTORY_BACKED_HTTP_FILES,
    EXPECTED_HTTP_INTEGRATION_FILES,
    EXPECTED_IMPLICIT_SEED_CONSUMERS,
    EXPECTED_SELF_CONTAINED_HTTP_FILES,
    FULL_SUITE_CI_READY,
    MOCKED_EXTERNAL_PROVIDER_FILES,
    REPOSITORY_ROOT,
    TESTS_ROOT,
    discover_direct_session_files,
    discover_http_integration_files,
    discover_implicit_seed_consumers,
)


def test_http_integration_inventory_is_explicit():
    assert discover_http_integration_files() == EXPECTED_HTTP_INTEGRATION_FILES


def test_implicit_seed_consumer_inventory_is_explicit():
    assert discover_implicit_seed_consumers() == EXPECTED_IMPLICIT_SEED_CONSUMERS


def test_self_contained_http_subset_is_explicit():
    self_contained = (
        discover_http_integration_files() - discover_implicit_seed_consumers()
        - EXPECTED_FACTORY_BACKED_HTTP_FILES
    )
    assert self_contained == EXPECTED_SELF_CONTAINED_HTTP_FILES


def test_direct_session_inventory_is_explicit():
    assert discover_direct_session_files() == EXPECTED_DIRECT_SESSION_FILES


def test_migrations_do_not_claim_to_seed_the_shared_test_identity():
    migration_text = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in sorted((BACKEND_ROOT / "alembic" / "versions").glob("*.py"))
    )
    assert "admin@example.com" not in migration_text


def test_external_provider_inventory_uses_test_doubles():
    for relative_path in MOCKED_EXTERNAL_PROVIDER_FILES:
        source = (TESTS_ROOT / relative_path).read_text(encoding="utf-8-sig")
        assert "MagicMock" in source or "patch(" in source


def test_ci_runs_full_suite_after_fixture_contract_is_replaced():
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "backend-validation.yml"
    ).read_text(encoding="utf-8")

    assert FULL_SUITE_CI_READY is True
    assert "python -m pytest -p no:cacheprovider -v" in workflow
    assert "tests/test_fixture_readiness.py" in workflow
