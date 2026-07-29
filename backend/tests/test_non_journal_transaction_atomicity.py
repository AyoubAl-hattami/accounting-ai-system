'''Focused rollback tests for audited non-journal business mutations.

These tests use a small session double so audit insertion failures can be
injected at the transaction boundary.
'''
from datetime import date
from types import SimpleNamespace

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.accounts.dto import (
    CreateAccountCommand,
    DefaultAccountDefinition,
    SeedDefaultAccountsCommand,
    UpdateAccountCommand,
)
from app.application.accounts.use_cases import (
    CreateAccount, SeedDefaultAccounts, UpdateAccount,
)
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.services import (
    account_service,
    audit_service,
    company_service,
    company_user_service,
    fiscal_service,
    journal_service,
)


class RecordingSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0
        self._next_id = 100

    def add(self, value):
        if value not in self.added:
            self.added.append(value)

    def flush(self):
        self.flushes += 1
        for value in self.added:
            if hasattr(value, 'id') and value.id is None:
                value.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        self.added.clear()


def _fail_audit(monkeypatch):
    def fail(**_kwargs):
        raise RuntimeError('audit insert failed')

    monkeypatch.setattr(audit_service, 'create_audit_log', fail)


def _assert_audit_failure_rolls_back(db, monkeypatch, entity):
    _fail_audit(monkeypatch)

    with pytest.raises(RuntimeError, match='audit insert failed'):
        audit_service.create_atomic_audit_log(
            db=db,
            company_id=getattr(entity, 'company_id', None),
            action='representative_audited_mutation',
            entity_type=entity.__class__.__name__.lower(),
            entity_id=entity.id,
        )

    assert db.commits == 0
    assert db.rollbacks == 1
    assert db.added == []


def test_account_creation_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    account = account_service.create_account(
        db,
        SimpleNamespace(
            company_id=7,
            code='1000',
            name='Cash',
            account_type='asset',
            parent_id=None,
            description=None,
            is_active=True,
            is_system=False,
        ),
    )

    _assert_audit_failure_rolls_back(db, monkeypatch, account)


def test_account_create_use_case_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    account = CreateAccount(SqlAlchemyAccountRepository(db)).execute(
        CreateAccountCommand(
            company_id=7,
            code=' 1000 ',
            name=' Cash ',
            account_type='asset',
            parent_id=None,
            description=None,
            is_active=True,
            is_system=False,
        )
    )

    assert account.code == '1000'
    assert account.name == 'Cash'
    _assert_audit_failure_rolls_back(db, monkeypatch, account)


def test_fiscal_year_creation_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    fiscal_year = fiscal_service.create_fiscal_year(
        db,
        SimpleNamespace(
            company_id=7,
            name='FY 2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status='open',
        ),
    )

    _assert_audit_failure_rolls_back(db, monkeypatch, fiscal_year)


def test_direct_company_user_add_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    membership = company_user_service.create_company_user(
        db,
        SimpleNamespace(company_id=7, user_id=9, role='accountant', is_active=True),
    )

    _assert_audit_failure_rolls_back(db, monkeypatch, membership)


def test_company_and_initial_membership_roll_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    company = company_service.create_company(
        db,
        SimpleNamespace(
            name='Atomic Company',
            legal_name=None,
            registration_no=None,
            tax_no=None,
            base_currency='eur',
            address=None,
            is_active=True,
        ),
    )
    company_user_service.create_company_user(
        db,
        SimpleNamespace(company_id=company.id, user_id=9, role='admin', is_active=True),
    )

    _assert_audit_failure_rolls_back(db, monkeypatch, company)


def test_opening_balance_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    opening_balance = journal_service.create_opening_balance_entry(
        db,
        SimpleNamespace(
            company_id=7,
            entry_no='OB-2026',
            entry_date=date(2026, 1, 1),
            description='Opening balance',
            lines=[
                SimpleNamespace(
                    account_id=10,
                    debit=100,
                    credit=0,
                    description='Opening debit',
                ),
                SimpleNamespace(
                    account_id=11,
                    debit=0,
                    credit=100,
                    description='Opening credit',
                ),
            ],
        ),
        SimpleNamespace(id=2),
        SimpleNamespace(id=3),
        9,
    )

    _assert_audit_failure_rolls_back(db, monkeypatch, opening_balance)


def test_account_update_use_case_rolls_back_staged_update_when_audit_insert_fails(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)
    try:
        with Session(engine) as db:
            company = Company(name="Atomic Update", base_currency="USD")
            db.add(company)
            db.flush()
            account = Account(company_id=company.id, code="1000", name="Before", account_type="asset", is_active=True, is_system=False)
            db.add(account)
            db.commit()
            account_id = account.id

            updated = UpdateAccount(SqlAlchemyAccountRepository(db)).execute(
                UpdateAccountCommand(account_id=account_id, name="After", fields=frozenset({"name"}))
            )
            assert updated.name == "After"
            _fail_audit(monkeypatch)
            with pytest.raises(RuntimeError, match="audit insert failed"):
                audit_service.create_atomic_audit_log(db=db, company_id=company.id, action="update_account", entity_type="account", entity_id=account_id)

        with Session(engine) as verification_db:
            assert verification_db.get(Account, account_id).name == "Before"
    finally:
        engine.dispose()

def test_seed_default_accounts_rolls_back_when_audit_insert_fails(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    Account.__table__.create(engine)
    try:
        with Session(engine) as db:
            company = Company(name="Atomic Seed", base_currency="USD")
            db.add(company)
            db.commit()
            company_id = company.id
            command = SeedDefaultAccountsCommand(
                company_id=company_id,
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

            seeded = SeedDefaultAccounts(SqlAlchemyAccountRepository(db)).execute(command)
            assert seeded.created_count == 2
            _fail_audit(monkeypatch)
            with pytest.raises(RuntimeError, match="audit insert failed"):
                audit_service.create_atomic_audit_log(
                    db=db,
                    company_id=company_id,
                    action="seed_default_accounts",
                    entity_type="account",
                )

        with Session(engine) as verification_db:
            assert verification_db.query(Account).count() == 0
    finally:
        engine.dispose()
