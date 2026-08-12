from unittest.mock import Mock, patch

import pytest

from scripts.cleanup_local_demo_data import (
    CleanupPlan,
    build_parser,
    cleanup_local_pollution,
    ensure_cleanup_environment,
    execute_cleanup,
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


def test_production_guard_blocks_confirmed_deletion():
    db = Mock()
    with patch("scripts.cleanup_local_demo_data.execute_cleanup") as execute:
        with pytest.raises(RuntimeError, match="APP_ENV=development"):
            cleanup_local_pollution(db, app_env="production", confirm=True)

    execute.assert_not_called()
    db.commit.assert_not_called()


def test_confirm_deletes_candidates_in_committed_batches(capsys):
    plan = CleanupPlan(
        company_ids=(1, 2, 3),
        company_names=("Company 1", "Company 2", "Company 3"),
        user_ids=(10, 11),
        user_emails=("one@accounting-ai-test.dev", "two@accounting-ai-test.dev"),
        row_counts={},
    )
    db = Mock()
    with (
        patch(
            "scripts.cleanup_local_demo_data.build_cleanup_plan",
            return_value=plan,
        ),
        patch(
            "scripts.cleanup_local_demo_data._delete_company_batch",
            side_effect=lambda _db, ids: len(ids),
        ) as delete_companies,
        patch(
            "scripts.cleanup_local_demo_data._delete_user_batch",
            side_effect=lambda _db, ids: len(ids),
        ) as delete_users,
    ):
        result = cleanup_local_pollution(
            db,
            app_env="development",
            confirm=True,
            batch_size=2,
        )

    assert result is plan
    assert [call.args[1] for call in delete_companies.call_args_list] == [(1, 2), (3,)]
    assert [call.args[1] for call in delete_users.call_args_list] == [(10, 11)]
    assert db.commit.call_count == 3
    output = capsys.readouterr().out
    assert "Starting confirmed cleanup: 5 candidates in 3 batches" in output
    assert "Batch 1/3 committed: deleted 2; deleted total 2; remaining candidates 3" in output
    assert "Cleanup complete: deleted 5 of 5 candidates" in output


def test_execute_cleanup_rolls_back_only_the_failed_batch():
    plan = CleanupPlan(
        company_ids=(1, 2, 3),
        company_names=("One", "Two", "Three"),
        user_ids=(),
        user_emails=(),
        row_counts={},
    )
    db = Mock()
    with patch(
        "scripts.cleanup_local_demo_data._delete_company_batch",
        side_effect=[2, RuntimeError("delete failed")],
    ):
        with pytest.raises(RuntimeError, match="delete failed"):
            execute_cleanup(db, plan, batch_size=2)

    assert db.commit.call_count == 1
    db.rollback.assert_called_once_with()


def test_batch_size_cli_option_works():
    args = build_parser().parse_args(["--confirm", "--batch-size", "250"])
    assert args.confirm is True
    assert args.batch_size == 250


@pytest.mark.parametrize("value", ["0", "-1"])
def test_batch_size_cli_option_rejects_non_positive_values(value):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--batch-size", value])


def test_verbose_mode_prints_individual_identifiers(capsys):
    plan = CleanupPlan(
        company_ids=tuple(range(1, 13)),
        company_names=tuple(f"Company {index}" for index in range(1, 13)),
        user_ids=(),
        user_emails=(),
        row_counts={},
    )
    db = Mock()
    with (
        patch(
            "scripts.cleanup_local_demo_data.build_cleanup_plan",
            return_value=plan,
        ),
        patch(
            "scripts.cleanup_local_demo_data._delete_company_batch",
            side_effect=lambda _db, ids: len(ids),
        ),
    ):
        cleanup_local_pollution(
            db,
            app_env="development",
            confirm=True,
            batch_size=12,
            verbose=True,
        )

    output = capsys.readouterr().out
    assert "[6] Company 6" in output
    assert "more (use --verbose" not in output
