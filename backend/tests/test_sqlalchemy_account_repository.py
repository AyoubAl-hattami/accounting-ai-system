import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.accounts.dto import (
    AccountDTO,
    CreateAccountCommand,
    DefaultAccountDefinition,
    SeedDefaultAccountsCommand,
    UpdateAccountCommand,
)
from app.core.database import Base
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company


class CountingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()


def test_repository_filters_orders_paginates_counts_and_includes_all_statuses():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)

    try:
        with Session(engine) as db:
            first_company = Company(name="First", base_currency="USD")
            second_company = Company(name="Second", base_currency="USD")
            db.add_all([first_company, second_company])
            db.flush()

            db.add_all(
                [
                    Account(
                        company_id=first_company.id,
                        code="3000",
                        name="Inactive",
                        account_type="expense",
                        is_active=False,
                        is_system=False,
                    ),
                    Account(
                        company_id=first_company.id,
                        code="1000",
                        name="System",
                        account_type="asset",
                        is_active=True,
                        is_system=True,
                    ),
                    Account(
                        company_id=first_company.id,
                        code="2000",
                        name="Ordinary",
                        account_type="liability",
                        is_active=True,
                        is_system=False,
                    ),
                    Account(
                        company_id=second_company.id,
                        code="0500",
                        name="Other company",
                        account_type="asset",
                        is_active=True,
                        is_system=True,
                    ),
                ]
            )
            db.flush()

            repository = SqlAlchemyAccountRepository(db)

            all_items = repository.list_by_company(
                company_id=first_company.id,
                skip=0,
                limit=100,
            )
            page = repository.list_by_company(
                company_id=first_company.id,
                skip=1,
                limit=1,
            )

            assert [item.code for item in all_items] == ["1000", "2000", "3000"]
            assert {item.company_id for item in all_items} == {first_company.id}
            assert [item.code for item in page] == ["2000"]
            assert repository.count_by_company(first_company.id) == 3
            assert repository.count_by_company(second_company.id) == 1
            assert any(item.is_system for item in all_items)
            assert any(not item.is_active for item in all_items)

            system_account = next(item for item in all_items if item.is_system)
            inactive_account = next(item for item in all_items if not item.is_active)
            other_company_account = repository.list_by_company(
                company_id=second_company.id,
                skip=0,
                limit=1,
            )[0]

            assert repository.get_by_id(system_account.id) == system_account
            assert repository.get_by_id(inactive_account.id) == inactive_account
            assert (
                repository.get_by_id(other_company_account.id)
                == other_company_account
            )
            assert repository.get_by_id(999_999) is None
    finally:
        engine.dispose()


def test_repository_create_flushes_maps_and_rolls_back_constraint_failure():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)

    try:
        with CountingSession(engine) as db:
            company = Company(name="Create Test", base_currency="USD")
            db.add(company)
            db.commit()
            db.commit_calls = 0

            repository = SqlAlchemyAccountRepository(db)
            command = CreateAccountCommand(
                company_id=company.id,
                code="7000",
                name="Created account",
                account_type="expense",
                parent_id=None,
                description="Description",
                is_active=False,
                is_system=True,
            )

            result = repository.create(command)

            assert isinstance(result, AccountDTO)
            assert result.id is not None
            assert result.created_at is not None
            assert result.updated_at is not None
            assert result.company_id == command.company_id
            assert result.code == command.code
            assert result.name == command.name
            assert result.account_type == command.account_type
            assert result.parent_id == command.parent_id
            assert result.description == command.description
            assert result.is_active == command.is_active
            assert result.is_system == command.is_system
            assert db.commit_calls == 0

            db.commit()
            db.commit_calls = 0

            with pytest.raises(IntegrityError):
                repository.create(command)

            assert db.is_active
            assert db.commit_calls == 0
            assert repository.count_by_company(company.id) == 1
    finally:
        engine.dispose()


def test_repository_update_mutates_only_supplied_fields_clears_parent_and_does_not_commit():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)
    try:
        with CountingSession(engine) as db:
            company = Company(name="Update Test", base_currency="USD")
            db.add(company)
            db.flush()
            parent = Account(company_id=company.id, code="1000", name="Parent", account_type="asset", is_active=True, is_system=False)
            account = Account(company_id=company.id, code="1100", name="Before", account_type="asset", parent_id=None, description="keep", is_active=True, is_system=False)
            db.add_all([parent, account])
            db.commit()
            account.parent_id = parent.id
            db.commit()
            db.commit_calls = 0

            result = SqlAlchemyAccountRepository(db).update(
                UpdateAccountCommand(
                    account_id=account.id,
                    name="After",
                    parent_id=None,
                    fields=frozenset({"name", "parent_id"}),
                )
            )

            assert isinstance(result, AccountDTO)
            assert result.name == "After"
            assert result.parent_id is None
            assert result.code == "1100"
            assert result.description == "keep"
            assert result.account_type == "asset"
            assert db.commit_calls == 0
    finally:
        engine.dispose()


def test_repository_update_constraint_failure_rolls_back_and_is_globally_keyed():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)
    try:
        with CountingSession(engine) as db:
            first = Company(name="First Update", base_currency="USD")
            second = Company(name="Second Update", base_currency="USD")
            db.add_all([first, second])
            db.flush()
            one = Account(company_id=first.id, code="1000", name="One", account_type="asset", is_active=True, is_system=False)
            duplicate = Account(company_id=first.id, code="2000", name="Duplicate", account_type="asset", is_active=True, is_system=False)
            global_target = Account(company_id=second.id, code="1000", name="Global", account_type="asset", is_active=True, is_system=False)
            db.add_all([one, duplicate, global_target])
            db.commit()
            db.commit_calls = 0
            repository = SqlAlchemyAccountRepository(db)

            global_result = repository.update(UpdateAccountCommand(account_id=global_target.id, name="Changed", fields=frozenset({"name"})))
            assert global_result.company_id == second.id
            assert global_result.name == "Changed"
            assert db.commit_calls == 0

            with pytest.raises(IntegrityError):
                repository.update(UpdateAccountCommand(account_id=one.id, code="2000", fields=frozenset({"code"})))

            assert db.is_active
            assert db.commit_calls == 0
            assert repository.get_by_id(one.id).code == "1000"
    finally:

        engine.dispose()

def test_repository_seed_defaults_stages_hierarchy_idempotently_without_commit():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)
    try:
        with CountingSession(engine) as db:
            company = Company(name="Repository Seed", base_currency="USD")
            db.add(company)
            db.commit()
            db.commit_calls = 0
            command = SeedDefaultAccountsCommand(
                company_id=company.id,
                accounts=(
                    DefaultAccountDefinition(
                        code="1000",
                        name="Assets",
                        account_type="asset",
                        parent_code=None,
                        description="Main assets category",
                        is_system=True,
                    ),
                    DefaultAccountDefinition(
                        code="1110",
                        name="Main Bank",
                        account_type="asset",
                        parent_code="1000",
                        description="Main company bank account",
                        is_system=True,
                    ),
                ),
            )
            repository = SqlAlchemyAccountRepository(db)

            first = repository.seed_defaults(command)
            second = repository.seed_defaults(command)

            assert first.created_count == 2
            assert first.skipped_count == 0
            assert [account.code for account in first.accounts] == ["1000", "1110"]
            assert first.accounts[1].parent_id == first.accounts[0].id
            assert all(account.is_system for account in first.accounts)
            assert second.created_count == 0
            assert second.skipped_count == 2
            assert second.accounts == []
            assert db.commit_calls == 0
    finally:
        engine.dispose()