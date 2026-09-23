from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.credit_notes.dto import (
    AllocateCreditNoteCommand,
    CreateCreditNoteAllocationCommand,
    CreateCreditNoteCommand,
    CreateCreditNoteLineCommand,
    PostCreditNoteCommand,
)
from app.application.reports.aging_dto import AgingQuery
from app.application.reports.statement_dto import PartnerStatementQuery
from app.application.invoices.dto import (
    CreateInvoiceCommand,
    CreateInvoiceLineCommand,
    PostInvoiceCommand,
)
from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.credit_note_repository import (
    SqlAlchemyCreditNoteRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.invoice_repository import (
    SqlAlchemyInvoiceRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.refund_repository import (
    SqlAlchemyRefundRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.credit_note import (
    CreditNote,
    CreditNoteAllocation,
    CreditNoteLine,
)
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.invoice import Invoice, InvoiceLine
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import Payment, PaymentAllocation
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
        Invoice.__table__,
        InvoiceLine.__table__,
        CreditNote.__table__,
        CreditNoteLine.__table__,
        CreditNoteAllocation.__table__,
        Payment.__table__,
        PaymentAllocation.__table__,
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
    session.add(
        Account(
            id=13,
            company_id=1,
            code="4000",
            name="Revenue USD",
            account_type="income",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=14,
            company_id=1,
            code="4100",
            name="Sales Returns USD",
            account_type="income",
            currency="USD",
            is_active=True,
        )
    )

    # Partner
    session.add(
        Partner(
            id=1,
            company_id=1,
            name="Acme Client",
            code="CUST01",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            is_active=True,
        )
    )

    session.commit()
    return session


def test_aging_report_with_credit_notes():
    db = _session()
    inv_repo = SqlAlchemyInvoiceRepository(db)
    cn_repo = SqlAlchemyCreditNoteRepository(db)
    rep_repo = SqlAlchemyReportRepository(db)

    # 1. Invoice for $1000
    inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-100",
            issue_date=date(2026, 1, 5),
            due_date=date(2026, 1, 15),
            currency="USD",
            lines=[
                CreateInvoiceLineCommand(
                    description="Consulting",
                    quantity=Decimal("10"),
                    unit_price=Decimal("100.00"),
                    account_id=13,
                )
            ],
        )
    )
    inv_repo.post(
        PostInvoiceCommand(
            invoice_id=inv.id,
            receivable_or_payable_account_id=11,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )

    # 2. Credit Note for $300 allocated to the invoice
    cn = cn_repo.create(
        CreateCreditNoteCommand(
            company_id=1,
            partner_id=1,
            note_type="customer_credit_note",
            credit_note_no="CN-100",
            issue_date=date(2026, 1, 10),
            currency="USD",
            lines=[
                CreateCreditNoteLineCommand(
                    description="Adjustment",
                    quantity=Decimal("1"),
                    unit_price=Decimal("300.00"),
                    account_id=14,
                )
            ],
        )
    )
    cn_repo.post(
        PostCreditNoteCommand(
            credit_note_id=cn.id,
            receivable_or_payable_account_id=11,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    cn_repo.allocate(
        AllocateCreditNoteCommand(
            credit_note_id=cn.id,
            allocations=[CreateCreditNoteAllocationCommand(invoice_id=inv.id, amount=Decimal("300.00"))],
        )
    )

    # 3. Check Aging Report as of Jan 25, 2026 (10 days overdue)
    aging = rep_repo.get_aging_report(
        AgingQuery(
            company_id=1,
            report_type="ar",
            as_of_date=date(2026, 1, 25),
            currency="USD",
        )
    )

    assert len(aging.items) == 1
    item = aging.items[0]
    assert item.invoice_no == "INV-100"
    assert item.original_amount == Decimal("1000.00")
    assert item.credited_amount == Decimal("300.00")
    assert item.paid_amount == Decimal("0.00")
    assert item.outstanding_amount == Decimal("700.00")
    assert item.days_overdue == 10
    assert item.bucket == "1-30"


def test_partner_statement_with_credit_notes_and_refunds():
    db = _session()
    inv_repo = SqlAlchemyInvoiceRepository(db)
    cn_repo = SqlAlchemyCreditNoteRepository(db)
    ref_repo = SqlAlchemyRefundRepository(db)
    rep_repo = SqlAlchemyReportRepository(db)

    # 1. Invoice on Jan 5: $1000
    inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-100",
            issue_date=date(2026, 1, 5),
            due_date=date(2026, 1, 20),
            currency="USD",
            lines=[
                CreateInvoiceLineCommand(
                    description="Consulting",
                    quantity=Decimal("10"),
                    unit_price=Decimal("100.00"),
                    account_id=13,
                )
            ],
        )
    )
    inv_repo.post(
        PostInvoiceCommand(
            invoice_id=inv.id,
            receivable_or_payable_account_id=11,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )

    # 2. Credit note on Jan 10: $300
    cn = cn_repo.create(
        CreateCreditNoteCommand(
            company_id=1,
            partner_id=1,
            note_type="customer_credit_note",
            credit_note_no="CN-100",
            issue_date=date(2026, 1, 10),
            currency="USD",
            lines=[
                CreateCreditNoteLineCommand(
                    description="Discount",
                    quantity=Decimal("1"),
                    unit_price=Decimal("300.00"),
                    account_id=14,
                )
            ],
        )
    )
    cn_repo.post(
        PostCreditNoteCommand(
            credit_note_id=cn.id,
            receivable_or_payable_account_id=11,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )

    # 3. Customer Refund on Jan 15: $150
    refund = ref_repo.create(
        CreateRefundCommand(
            company_id=1,
            partner_id=1,
            refund_type="customer_refund",
            currency_code="USD",
            amount=Decimal("150.00"),
            refund_date=date(2026, 1, 15),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=11,
        )
    )
    ref_repo.post(
        PostRefundCommand(
            refund_id=refund.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )

    # 4. Generate Partner Statement for Jan 1 to Jan 31
    statement = rep_repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
    )

    assert statement.partner_id == 1
    assert len(statement.transactions) == 3

    t_inv = statement.transactions[0]
    assert t_inv.type == "invoice"
    assert t_inv.debit == Decimal("1000.00")
    assert t_inv.credit == Decimal("0.00")
    assert t_inv.running_balance == Decimal("1000.00")

    t_cn = statement.transactions[1]
    assert t_cn.type == "credit_note"
    assert t_cn.debit == Decimal("0.00")
    assert t_cn.credit == Decimal("300.00")
    assert t_cn.running_balance == Decimal("700.00")

    t_ref = statement.transactions[2]
    assert t_ref.type == "refund"
    assert t_ref.debit == Decimal("150.00")
    assert t_ref.credit == Decimal("0.00")
    assert t_ref.running_balance == Decimal("850.00")

    assert statement.total_debit == Decimal("1150.00")
    assert statement.total_credit == Decimal("300.00")
    assert statement.closing_balance == Decimal("850.00")
