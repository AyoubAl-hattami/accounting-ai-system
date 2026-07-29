import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.accounts.dto import AccountDTO, CreateAccountCommand
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
