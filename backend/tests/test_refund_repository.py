from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
    RefundQuery,
    VoidRefundCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.refund_repository import (
    SqlAlchemyRefundRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.credit_note import CreditNote
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.refund import Refund
from app.modules.accounting.models.user import User


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        Company.__table__,
        User.__table__,
        Account.__table__,
        FiscalYear.__table__,
        FiscalPeriod.__table__,
        Partner.__table__,
        JournalEntry.__table__,
        JournalLine.__table__,
        Refund.__table__,
    ):
        table.create(bind=engine)

    session = Session(engine)
    session.add(Company(id=1, name="Acme Inc", base_currency="USD", is_active=True))

    session.add(
        FiscalYear(
            id=1,
            company_id=1,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="open",
        )
    )
    session.add(
        FiscalPeriod(
            id=1,
            company_id=1,
            fiscal_year_id=1,
            period_no=1,
            name="Jan 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status="open",
        )
    )

    # Accounts
    session.add(
        Account(
            id=10,
            company_id=1,
            code="1010",
            name="Bank USD",
            account_type="asset",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=11,
            company_id=1,
            code="1200",
            name="AR USD",
            account_type="asset",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=12,
            company_id=1,
            code="2000",
            name="AP USD",
            account_type="liability",
            currency="USD",
            is_active=True,
        )
    )

    # Partners
    session.add(
        Partner(
            id=1,
            company_id=1,
            name="Customer Alpha",
            code="CUST01",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=2,
            company_id=1,
            name="Vendor Beta",
            code="VEND01",
            is_customer=False,
            is_vendor=True,
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=3,
            company_id=1,
            name="EUR Customer",
            code="CUST02",
            is_customer=True,
            is_vendor=False,
            currency="EUR",
            is_active=True,
        )
    )

    session.commit()
    return session


def test_create_and_post_customer_refund():
    db = _session()
    repo = SqlAlchemyRefundRepository(db)

    cmd = CreateRefundCommand(
        company_id=1,
        partner_id=1,
        refund_type="customer_refund",
        currency_code="USD",
        amount=Decimal("150.00"),
        refund_date=date(2026, 1, 20),
        bank_or_cash_account_id=10,  # Bank
        receivable_or_payable_account_id=11,  # AR
        reference="REF-001",
        memo="Refund overpayment",
    )

    refund = repo.create(cmd)
    assert refund.id is not None
    assert refund.status == "draft"
    assert refund.amount == Decimal("150.00")

    # Post
    posted = repo.post(
        PostRefundCommand(
            refund_id=refund.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    assert posted.status == "posted"
    assert posted.journal_entry_id is not None

    # Check journal entry: Customer refund pays money back to customer
    # Debit AR (11) 150, Credit Bank (10) 150
    je = db.query(JournalEntry).filter(JournalEntry.id == posted.journal_entry_id).first()
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == je.id).all()
    assert len(lines) == 2

    debit_line = next(l for l in lines if l.debit > 0)
    credit_line = next(l for l in lines if l.credit > 0)
    assert debit_line.account_id == 11
    assert debit_line.debit == Decimal("150.00")
    assert credit_line.account_id == 10
    assert credit_line.credit == Decimal("150.00")


def test_create_and_post_vendor_refund():
    db = _session()
    repo = SqlAlchemyRefundRepository(db)

    cmd = CreateRefundCommand(
        company_id=1,
        partner_id=2,
        refund_type="vendor_refund",
        currency_code="USD",
        amount=Decimal("250.00"),
        refund_date=date(2026, 1, 20),
        bank_or_cash_account_id=10,  # Bank
        receivable_or_payable_account_id=12,  # AP
    )

    refund = repo.create(cmd)
    posted = repo.post(
        PostRefundCommand(
            refund_id=refund.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    assert posted.status == "posted"

    # Vendor refund receives money back from vendor
    # Debit Bank (10) 250, Credit AP (12) 250
    je = db.query(JournalEntry).filter(JournalEntry.id == posted.journal_entry_id).first()
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == je.id).all()
    debit_line = next(l for l in lines if l.debit > 0)
    credit_line = next(l for l in lines if l.credit > 0)
    assert debit_line.account_id == 10
    assert debit_line.debit == Decimal("250.00")
    assert credit_line.account_id == 12
    assert credit_line.credit == Decimal("250.00")


def test_void_refund():
    db = _session()
    repo = SqlAlchemyRefundRepository(db)

    cmd = CreateRefundCommand(
        company_id=1,
        partner_id=1,
        refund_type="customer_refund",
        currency_code="USD",
        amount=Decimal("100.00"),
        refund_date=date(2026, 1, 20),
        bank_or_cash_account_id=10,
        receivable_or_payable_account_id=11,
    )
    refund = repo.create(cmd)
    posted = repo.post(
        PostRefundCommand(
            refund_id=refund.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )

    # Void posted refund
    voided = repo.void(VoidRefundCommand(refund_id=posted.id))
    assert voided.status == "void"

    # Verify journal entry status is void
    je = db.query(JournalEntry).filter(JournalEntry.id == posted.journal_entry_id).first()
    assert je is not None
    assert je.status == "void"


def test_refund_currency_validation():
    db = _session()
    repo = SqlAlchemyRefundRepository(db)

    # Partner 3 is EUR, refund is USD -> should fail
    with pytest.raises(ValueError, match="does not match"):
        repo.create(
            CreateRefundCommand(
                company_id=1,
                partner_id=3,
                refund_type="customer_refund",
                currency_code="USD",
                amount=Decimal("100.00"),
                refund_date=date(2026, 1, 20),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
            )
        )
