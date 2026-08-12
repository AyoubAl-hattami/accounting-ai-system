from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from scripts.cleanup_local_demo_data import (
    COMPANY_DEPENDENT_TABLES,
    JOURNAL_CHILD_TABLES,
    CleanupPlan,
    _candidate_companies,
    _candidate_users,
    _delete_company_batch,
    _delete_company_rows_if_table_exists,
    _delete_journal_children_if_tables_exist,
    _delete_user_rows_if_table_exists,
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


@pytest.fixture
def candidate_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    User.__table__.create(engine)
    CompanyUser.__table__.create(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE accounts ("
            "id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL "
            "REFERENCES companies(id) ON DELETE RESTRICT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE journal_entries ("
            "id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL "
            "REFERENCES companies(id) ON DELETE RESTRICT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE company_subscriptions ("
            "id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL UNIQUE "
            "REFERENCES companies(id) ON DELETE RESTRICT, "
            "status VARCHAR(20) NOT NULL)"
        )
    with Session(engine) as db:
        yield db


def _add_user(db: Session, email: str, *, is_superuser: bool = False) -> User:
    user = User(
        email=email,
        hashed_password="not-a-real-password-hash",
        is_superuser=is_superuser,
    )
    db.add(user)
    return user


def _add_subscription(db: Session, company_id: int) -> None:
    db.execute(
        text(
            "INSERT INTO company_subscriptions (company_id, status) "
            "VALUES (:company_id, 'active')"
        ),
        {"company_id": company_id},
    )


@pytest.mark.parametrize(
    "company_name",
    (
        "CrossTenantA_factory",
        "CrossTenantB_factory",
        "SameCompany_factory",
        "CompanyA_factory",
        "CompanyB_factory",
        "Deterministic Company 42",
        "Test Company 42",
    ),
)
def test_candidate_company_patterns_include_remaining_test_clients(
    candidate_db, company_name
):
    candidate = Company(name=company_name)
    retained = Company(name="Example Consulting LLC")
    candidate_db.add_all((candidate, retained))
    candidate_db.flush()

    companies = _candidate_companies(candidate_db, ())

    assert [company.id for company in companies] == [candidate.id]


def test_empty_subscribed_other_co_is_cleanup_candidate(candidate_db):
    company = Company(name="Other Co")
    candidate_db.add(company)
    candidate_db.flush()
    _add_subscription(candidate_db, company.id)

    companies = _candidate_companies(candidate_db, ())

    assert [candidate.id for candidate in companies] == [company.id]


def test_other_co_with_membership_is_protected(candidate_db):
    company = Company(name="Other Co")
    user = _add_user(candidate_db, "owner@local.invalid")
    candidate_db.add(company)
    candidate_db.flush()
    candidate_db.add(CompanyUser(company_id=company.id, user_id=user.id, role="admin"))
    _add_subscription(candidate_db, company.id)
    candidate_db.flush()

    assert _candidate_companies(candidate_db, ()) == []


@pytest.mark.parametrize("dependent_table", ["accounts", "journal_entries"])
def test_other_co_with_accounting_data_is_protected(candidate_db, dependent_table):
    company = Company(name="Other Co")
    candidate_db.add(company)
    candidate_db.flush()
    _add_subscription(candidate_db, company.id)
    candidate_db.execute(
        text(f"INSERT INTO {dependent_table} (company_id) VALUES (:company_id)"),
        {"company_id": company.id},
    )

    assert _candidate_companies(candidate_db, ()) == []


def test_other_co_without_subscription_is_protected(candidate_db):
    company = Company(name="Other Co")
    candidate_db.add(company)
    candidate_db.flush()

    assert _candidate_companies(candidate_db, ()) == []


@pytest.mark.parametrize(
    "company_name",
    ("Other Company", "Other Co ABC", "Demo Company Ltd", "ayoub", "ASAAS", "Alqassam"),
)
def test_similar_demo_and_local_company_names_are_protected(candidate_db, company_name):
    company = Company(name=company_name)
    candidate_db.add(company)
    candidate_db.flush()
    _add_subscription(candidate_db, company.id)

    assert _candidate_companies(candidate_db, ()) == []


def test_candidate_example_users_require_test_prefix_or_test_company(candidate_db):
    test_company = Company(name="CrossTenantA_membership")
    real_company = Company(name="Example Consulting LLC")
    candidate_db.add_all((test_company, real_company))
    prefixed_users = [
        _add_user(candidate_db, f"{prefix}factory@example.com")
        for prefix in (
            "cross_tenant_",
            "same_company_",
            "admin_a_",
            "admin_b_",
            "user_a_",
            "user_b_",
            "test_",
        )
    ]
    attached_user = _add_user(candidate_db, "ordinary_member@example.com")
    retained_user = _add_user(candidate_db, "ordinary@example.com")
    retained_member = _add_user(candidate_db, "real_company_member@example.com")
    protected_superuser = _add_user(
        candidate_db,
        "cross_tenant_platform@example.com",
        is_superuser=True,
    )
    candidate_db.flush()
    candidate_db.add_all(
        (
            CompanyUser(
                company_id=test_company.id,
                user_id=attached_user.id,
                role="admin",
            ),
            CompanyUser(
                company_id=real_company.id,
                user_id=retained_member.id,
                role="admin",
            ),
        )
    )
    candidate_db.flush()

    users = _candidate_users(candidate_db, (test_company.id,))
    candidate_ids = {user.id for user in users}

    assert {user.id for user in prefixed_users} <= candidate_ids
    assert attached_user.id in candidate_ids
    assert retained_user.id not in candidate_ids
    assert retained_member.id not in candidate_ids
    assert protected_superuser.id not in candidate_ids


def test_expanded_candidates_appear_in_dry_run(candidate_db, capsys):
    company = Company(name="SameCompany_dry_run")
    user = _add_user(candidate_db, "same_company_admin_dry_run@example.com")
    candidate_db.add(company)
    candidate_db.flush()
    candidate_db.add(
        CompanyUser(company_id=company.id, user_id=user.id, role="admin")
    )
    candidate_db.flush()

    with patch("scripts.cleanup_local_demo_data._count", return_value=0):
        plan = cleanup_local_pollution(candidate_db, app_env="development")

    assert plan.company_ids == (company.id,)
    assert plan.user_ids == (user.id,)
    assert "Candidate companies : 1" in capsys.readouterr().out
    candidate_db.rollback()


def test_confirm_deletes_expanded_company_and_user_candidates(candidate_db, capsys):
    company = Company(name="CompanyA_confirm")
    user = _add_user(candidate_db, "admin_a_confirm@example.com")
    candidate_db.add(company)
    candidate_db.flush()
    company_id = company.id
    user_id = user.id
    candidate_db.add(
        CompanyUser(company_id=company_id, user_id=user_id, role="admin")
    )
    candidate_db.commit()

    with patch("scripts.cleanup_local_demo_data._count", return_value=0):
        plan = cleanup_local_pollution(
            candidate_db,
            app_env="development",
            confirm=True,
            batch_size=1,
        )

    assert plan.company_ids == (company_id,)
    assert plan.user_ids == (user_id,)
    assert candidate_db.get(Company, company_id) is None
    assert candidate_db.get(User, user_id) is None
    output = capsys.readouterr().out
    assert "Cleanup complete: deleted 2 of 2 candidates" in output


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


def test_company_batch_deletes_legacy_journals_before_company_rows():
    db = Mock()
    company_delete_result = Mock(rowcount=2)
    db.execute.return_value = company_delete_result
    deletion_order: list[str] = []

    def record_table(_db, _inspector, table_name, _company_ids):
        deletion_order.append(table_name)
        return 0

    def record_journal_child(_db, _inspector, table_name, _company_ids):
        deletion_order.append(table_name)
        return 0

    with (
        patch("scripts.cleanup_local_demo_data.inspect", return_value=Mock()),
        patch("scripts.cleanup_local_demo_data._clear_self_reference_if_table_exists"),
        patch(
            "scripts.cleanup_local_demo_data._delete_company_rows_if_table_exists",
            side_effect=record_table,
        ),
        patch(
            "scripts.cleanup_local_demo_data._delete_journal_children_if_tables_exist",
            side_effect=record_journal_child,
        ),
    ):
        deleted = _delete_company_batch(db, (4, 5))

    assert deleted == 2
    expected_order = list(COMPANY_DEPENDENT_TABLES)
    journals_index = expected_order.index("journals")
    expected_order[journals_index:journals_index] = JOURNAL_CHILD_TABLES
    assert deletion_order == expected_order
    assert deletion_order.index("journal_entries") < deletion_order.index("journals")
    assert deletion_order.index("journal_sequences") < deletion_order.index("journals")
    db.execute.assert_called_once()


def test_delete_journal_sequences_through_legacy_journals():
    db = Mock()
    db.execute.return_value = Mock(rowcount=4)
    schema_inspector = Mock()
    schema_inspector.has_table.return_value = True
    schema_inspector.get_columns.side_effect = lambda table_name: {
        "journal_sequences": [{"name": "id"}, {"name": "journal_id"}],
        "journals": [{"name": "id"}, {"name": "company_id"}],
    }[table_name]

    deleted = _delete_journal_children_if_tables_exist(
        db,
        schema_inspector,
        "journal_sequences",
        (6904, 6905),
    )

    assert deleted == 4
    statement = str(db.execute.call_args.args[0])
    assert 'DELETE FROM "journal_sequences" WHERE journal_id IN' in statement
    assert 'SELECT id FROM "journals" WHERE company_id IN' in statement
    assert db.execute.call_args.args[1] == {"company_ids": (6904, 6905)}


@pytest.mark.parametrize("missing_table", ["journal_sequences", "journals"])
def test_delete_journal_sequences_skips_missing_optional_tables(missing_table):
    db = Mock()
    schema_inspector = Mock()
    schema_inspector.has_table.side_effect = lambda table_name: (
        table_name != missing_table
    )
    schema_inspector.get_columns.side_effect = lambda table_name: {
        "journal_sequences": [{"name": "journal_id"}],
        "journals": [{"name": "id"}, {"name": "company_id"}],
    }[table_name]

    deleted = _delete_journal_children_if_tables_exist(
        db,
        schema_inspector,
        "journal_sequences",
        (6904,),
    )

    assert deleted == 0
    db.execute.assert_not_called()


def test_delete_if_table_exists_handles_legacy_journals_table():
    db = Mock()
    db.execute.return_value = Mock(rowcount=3)
    schema_inspector = Mock()
    schema_inspector.has_table.return_value = True
    schema_inspector.get_columns.return_value = [
        {"name": "id"},
        {"name": "company_id"},
    ]

    deleted = _delete_company_rows_if_table_exists(
        db,
        schema_inspector,
        "journals",
        (4, 5),
    )

    assert deleted == 3
    statement = str(db.execute.call_args.args[0])
    assert 'DELETE FROM "journals"' in statement
    assert db.execute.call_args.args[1] == {"company_ids": (4, 5)}


def test_delete_if_table_exists_skips_missing_optional_table():
    db = Mock()
    schema_inspector = Mock()
    schema_inspector.has_table.return_value = False

    deleted = _delete_company_rows_if_table_exists(
        db,
        schema_inspector,
        "journals",
        (4,),
    )

    assert deleted == 0
    db.execute.assert_not_called()


def test_delete_user_rows_uses_only_columns_present_on_optional_table():
    db = Mock()
    db.execute.return_value = Mock(rowcount=2)
    schema_inspector = Mock()
    schema_inspector.has_table.return_value = True
    schema_inspector.get_columns.return_value = [
        {"name": "id"},
        {"name": "invited_by_user_id"},
        {"name": "accepted_by_user_id"},
    ]

    deleted = _delete_user_rows_if_table_exists(
        db,
        schema_inspector,
        "company_user_invitations",
        ("invited_by_user_id", "accepted_by_user_id", "missing_user_id"),
        (10, 11),
    )

    assert deleted == 2
    statement = str(db.execute.call_args.args[0])
    assert '"invited_by_user_id" IN' in statement
    assert '"accepted_by_user_id" IN' in statement
    assert "missing_user_id" not in statement
    assert db.execute.call_args.args[1] == {"user_ids": (10, 11)}


def test_confirm_deletes_standalone_test_user_and_dependencies(capsys):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    User.__table__.create(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql(
            "CREATE TABLE assistant_conversations ("
            "id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT)"
        )

    with Session(engine) as db:
        candidate = User(
            email="standalone@accounting-ai-test.dev",
            hashed_password="not-a-real-password-hash",
            is_superuser=False,
        )
        retained = User(
            email="retained@example.com",
            hashed_password="not-a-real-password-hash",
            is_superuser=False,
        )
        db.add_all((candidate, retained))
        db.flush()
        candidate_id = candidate.id
        retained_id = retained.id
        db.execute(
            text(
                "INSERT INTO assistant_conversations (id, user_id) "
                "VALUES (1, :user_id)"
            ),
            {"user_id": candidate_id},
        )
        db.commit()

        plan = CleanupPlan(
            company_ids=(),
            company_names=(),
            user_ids=(candidate_id,),
            user_emails=(candidate.email,),
            row_counts={"assistant_conversations": 1},
        )
        deleted = execute_cleanup(db, plan, batch_size=25)

        assert deleted == 1
        assert db.get(User, candidate_id) is None
        assert db.get(User, retained_id) is not None
        assert db.scalar(text("SELECT count(*) FROM assistant_conversations")) == 0

    output = capsys.readouterr().out
    assert "Batch 1/1 committed: deleted 1; deleted total 1" in output
    assert "Cleanup complete: deleted 1 of 1 candidates" in output


def test_failed_batch_prints_foreign_key_table_and_constraint(capsys):
    plan = CleanupPlan(
        company_ids=(4,),
        company_names=("Blocked Company",),
        user_ids=(),
        user_emails=(),
        row_counts={},
    )
    diagnostics = Mock(
        table_name="journals",
        constraint_name="journals_company_id_fkey",
        message_detail="Key (id)=(4) is referenced from table journals.",
    )
    blocker = RuntimeError("restricted")
    blocker.orig = Mock(diag=diagnostics)
    db = Mock()

    with patch(
        "scripts.cleanup_local_demo_data._delete_company_batch",
        side_effect=blocker,
    ):
        with pytest.raises(RuntimeError, match="restricted"):
            execute_cleanup(db, plan, batch_size=1)

    output = capsys.readouterr().out
    assert "table=journals" in output
    assert "constraint=journals_company_id_fkey" in output
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
