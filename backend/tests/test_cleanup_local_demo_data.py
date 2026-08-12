from unittest.mock import Mock, patch

import pytest

from scripts.cleanup_local_demo_data import (
    CleanupPlan,
    cleanup_local_pollution,
    ensure_cleanup_environment,
)


EMPTY_PLAN = CleanupPlan(
    company_ids=(),
    company_names=(),
    user_ids=(),
    user_emails=(),
    row_counts={},
)


@pytest.mark.parametrize("app_env", ["production", "staging", "test", ""])
def test_cleanup_refuses_every_non_development_environment(app_env):
    with pytest.raises(RuntimeError, match="APP_ENV=development"):
        ensure_cleanup_environment(app_env)


def test_cleanup_dry_run_never_executes_deletes(capsys):
    db = Mock()
    with (
        patch(
            "scripts.cleanup_local_demo_data.build_cleanup_plan",
            return_value=EMPTY_PLAN,
        ),
        patch("scripts.cleanup_local_demo_data.execute_cleanup") as execute,
    ):
        result = cleanup_local_pollution(db, app_env="development")

    assert result is EMPTY_PLAN
    execute.assert_not_called()
    db.commit.assert_not_called()
    assert "DRY RUN" in capsys.readouterr().out


def test_cleanup_requires_explicit_confirmation_before_execution():
    db = Mock()
    with (
        patch(
            "scripts.cleanup_local_demo_data.build_cleanup_plan",
            return_value=EMPTY_PLAN,
        ),
        patch("scripts.cleanup_local_demo_data.execute_cleanup") as execute,
    ):
        cleanup_local_pollution(db, app_env="development", confirm=True)

    execute.assert_called_once_with(db, EMPTY_PLAN)
