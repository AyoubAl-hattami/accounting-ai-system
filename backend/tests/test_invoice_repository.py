from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    CreateInvoiceLineCommand,
    InvoiceQuery,
    PostInvoiceCommand,
    UpdateInvoiceCommand,
    VoidInvoiceCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.invoice_repository import (
    SqlAlchemyInvoiceRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.invoice import Invoice, InvoiceLine
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import Payment, PaymentAllocation
from app.modules.accounting.models.user import User


def _session():
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
        Payment.__table__,
        PaymentAllocation.__table__,
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
    # USD Accounts
    session.add(
        Account(
            id=10,
            company_id=1,
            code="1100",
            name="Accounts Receivable",
            account_type="asset",
            account_subtype="receivable",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=20,
            company_id=1,
            code="4100",
            name="Sales Revenue",
            account_type="income",
            account_subtype="revenue",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=30,
            company_id=1,
            code="2100",
            name="Accounts Payable",
            account_type="liability",
            account_subtype="payable",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=40,
            company_id=1,
            code="5100",
            name="Office Supplies Expense",
            account_type="expense",
            account_subtype="expense",
            currency="USD",
            is_active=True,
        )
    )
    # YER Accounts (for currency mismatch testing)
    session.add(
        Account(
            id=50,
            company_id=1,
            code="1100-YER",
            name="Accounts Receivable YER",
            account_type="asset",
            account_subtype="receivable",
            currency="YER",
            is_active=True,
        )
    )
    # Partner
    session.add(
        Partner(
            id=1,
            company_id=1,
            name="Client A",
            code="CL-01",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            receivable_account_id=10,
        )
    )
    session.add(
        Partner(
            id=2,
            company_id=1,
            name="Supplier B",
            code="SUP-01",
            is_customer=False,
            is_vendor=True,
            currency="USD",
            payable_account_id=30,
        )
    )
    session.commit()
    return session


def test_sales_invoice_creation_totals_and_gl_posting():
    db = _session()
    repo = SqlAlchemyInvoiceRepository(db)

    # 1. Create a sales invoice with 2 lines
    cmd = CreateInvoiceCommand(
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-2026-001",
        issue_date=date(2026, 1, 15),
        due_date=date(2026, 2, 15),
        currency="USD",
        reference="PO-990",
        tax_amount=Decimal("15.00"),
        notes="Consulting services",
        lines=[
            CreateInvoiceLineCommand(
                description="Software Architecture",
                quantity=Decimal("10.0000"),
                unit_price=Decimal("100.00"),
                account_id=20,  # Sales Revenue
            ),
            CreateInvoiceLineCommand(
                description="Deployment Setup",
                quantity=Decimal("1.0000"),
                unit_price=Decimal("200.00"),
                account_id=20,  # Sales Revenue
            ),
        ],
    )

    inv = repo.create(cmd)
    db.commit()

    assert inv.id is not None
    assert inv.status == "draft"
    assert inv.subtotal == Decimal("1200.00")
    assert inv.tax_amount == Decimal("15.00")
    assert inv.total_amount == Decimal("1215.00")
    assert len(inv.lines) == 2

    # 2. Post the invoice to General Ledger
    post_cmd = PostInvoiceCommand(
        invoice_id=inv.id,
        receivable_or_payable_account_id=10,  # Accounts Receivable
        fiscal_year_id=1,
        fiscal_period_id=1,
    )
    posted_inv = repo.post(post_cmd)
    db.commit()

    assert posted_inv.status == "posted"
    assert posted_inv.journal_entry_id is not None

    # 3. Verify the generated journal entry
    entry = db.query(JournalEntry).filter(JournalEntry.id == posted_inv.journal_entry_id).one()
    assert entry.status == "posted"
    assert entry.source_type == "out_invoice"
    assert entry.source_id == str(inv.id)
    assert len(entry.lines) == 3

    # Check debit (AR)
    ar_line = next(line for line in entry.lines if line.account_id == 10)
    assert ar_line.debit == Decimal("1215.00")
    assert ar_line.credit == Decimal("0.00")

    # Check credit (Revenue lines)
    rev_lines = [line for line in entry.lines if line.account_id == 20]
    assert len(rev_lines) == 2
    assert sum(line.credit for line in rev_lines) == Decimal("1200.00")

    # 4. Refuse posting with mismatched currency
    # Try posting an invoice in YER against USD AR account
    yer_inv_cmd = CreateInvoiceCommand(
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-2026-YER",
        issue_date=date(2026, 1, 15),
        due_date=date(2026, 2, 15),
        currency="YER",
        lines=[
            CreateInvoiceLineCommand(
                description="Item",
                quantity=Decimal("1.0000"),
                unit_price=Decimal("50000.00"),
                account_id=20,  # Account 20 is USD!
            ),
        ],
    )
    yer_inv = repo.create(yer_inv_cmd)
    db.commit()

    with pytest.raises(ValueError, match="does not match invoice currency"):
        repo.post(
            PostInvoiceCommand(
                invoice_id=yer_inv.id,
                receivable_or_payable_account_id=10,  # USD
                fiscal_year_id=1,
                fiscal_period_id=1,
            )
        )


def test_purchase_bill_and_void_workflow():
    db = _session()
    repo = SqlAlchemyInvoiceRepository(db)

    # 1. Create a purchase bill
    cmd = CreateInvoiceCommand(
        company_id=1,
        partner_id=2,
        invoice_type="in_invoice",
        invoice_no="BILL-2026-001",
        issue_date=date(2026, 1, 10),
        due_date=date(2026, 2, 10),
        currency="USD",
        lines=[
            CreateInvoiceLineCommand(
                description="Paper & Pens",
                quantity=Decimal("5.0000"),
                unit_price=Decimal("20.00"),
                account_id=40,  # Expense
            ),
        ],
    )
    bill = repo.create(cmd)
    db.commit()

    assert bill.total_amount == Decimal("100.00")

    # 2. Post the purchase bill
    posted_bill = repo.post(
        PostInvoiceCommand(
            invoice_id=bill.id,
            receivable_or_payable_account_id=30,  # Accounts Payable
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    db.commit()

    assert posted_bill.status == "posted"
    entry = db.query(JournalEntry).filter(JournalEntry.id == posted_bill.journal_entry_id).one()
    assert entry.status == "posted"

    # Line 1: Debit Expense 100.00
    exp_line = next(l for l in entry.lines if l.account_id == 40)
    assert exp_line.debit == Decimal("100.00")
    # Line 2: Credit AP 100.00
    ap_line = next(l for l in entry.lines if l.account_id == 30)
    assert ap_line.credit == Decimal("100.00")

    # 3. Void the purchase bill
    voided = repo.void(VoidInvoiceCommand(invoice_id=bill.id))
    db.commit()

    assert voided.status == "void"
    db.refresh(entry)
    assert entry.status == "void"
