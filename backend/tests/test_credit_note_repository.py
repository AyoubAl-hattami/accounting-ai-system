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
    CreditNoteQuery,
    PostCreditNoteCommand,
    VoidCreditNoteCommand,
)
from app.application.invoices.dto import (
    CreateInvoiceCommand,
    CreateInvoiceLineCommand,
    PostInvoiceCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.credit_note_repository import (
    SqlAlchemyCreditNoteRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.invoice_repository import (
    SqlAlchemyInvoiceRepository,
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
    ):
        table.create(bind=engine)

    session = Session(engine)
    session.add(Company(id=1, name="Acme Inc", base_currency="USD", is_active=True))
    session.add(Company(id=2, name="Other Corp", base_currency="USD", is_active=True))

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
            name="Sales Revenue USD",
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
    session.add(
        Account(
            id=15,
            company_id=1,
            code="5000",
            name="Purchases Expense USD",
            account_type="expense",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=16,
            company_id=1,
            code="5100",
            name="Purchase Returns USD",
            account_type="expense",
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


def test_create_and_post_customer_credit_note():
    db = _session()
    repo = SqlAlchemyCreditNoteRepository(db)

    cmd = CreateCreditNoteCommand(
        company_id=1,
        partner_id=1,
        note_type="customer_credit_note",
        credit_note_no="CN-001",
        issue_date=date(2026, 1, 15),
        currency="USD",
        lines=[
            CreateCreditNoteLineCommand(
                description="Return defective item",
                quantity=Decimal("2"),
                unit_price=Decimal("150.00"),
                account_id=14,  # Sales Returns
            )
        ],
        tax_amount=Decimal("0.00"),
        reason="Defective goods",
    )

    cn = repo.create(cmd)
    assert cn.id is not None
    assert cn.status == "draft"
    assert cn.total_amount == Decimal("300.00")
    assert cn.unallocated_amount == Decimal("300.00")
    assert cn.allocated_amount == Decimal("0.00")

    # Post to ledger
    post_cmd = PostCreditNoteCommand(
        credit_note_id=cn.id,
        receivable_or_payable_account_id=11,  # AR
        fiscal_year_id=1,
        fiscal_period_id=1,
    )
    posted = repo.post(post_cmd)
    assert posted.status == "posted"
    assert posted.journal_entry_id is not None

    # Check journal entry: Debit Sales Returns 300, Credit AR 300
    je = db.query(JournalEntry).filter(JournalEntry.id == posted.journal_entry_id).first()
    assert je is not None
    assert je.status == "posted"
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == je.id).all()
    assert len(lines) == 2

    debit_line = next(line for line in lines if line.debit > 0)
    credit_line = next(line for line in lines if line.credit > 0)
    assert debit_line.account_id == 14
    assert debit_line.debit == Decimal("300.00")
    assert credit_line.account_id == 11
    assert credit_line.credit == Decimal("300.00")


def test_create_and_post_vendor_debit_note():
    db = _session()
    repo = SqlAlchemyCreditNoteRepository(db)

    cmd = CreateCreditNoteCommand(
        company_id=1,
        partner_id=2,
        note_type="vendor_debit_note",
        credit_note_no="DN-001",
        issue_date=date(2026, 1, 15),
        currency="USD",
        lines=[
            CreateCreditNoteLineCommand(
                description="Overcharged materials",
                quantity=Decimal("1"),
                unit_price=Decimal("200.00"),
                account_id=16,  # Purchase Returns
            )
        ],
        tax_amount=Decimal("0.00"),
    )

    dn = repo.create(cmd)
    post_cmd = PostCreditNoteCommand(
        credit_note_id=dn.id,
        receivable_or_payable_account_id=12,  # AP
        fiscal_year_id=1,
        fiscal_period_id=1,
    )
    posted = repo.post(post_cmd)
    assert posted.status == "posted"

    # Journal Entry: Debit AP 200, Credit Purchase Returns 200
    je = db.query(JournalEntry).filter(JournalEntry.id == posted.journal_entry_id).first()
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == je.id).all()
    debit_line = next(line for line in lines if line.debit > 0)
    credit_line = next(line for line in lines if line.credit > 0)
    assert debit_line.account_id == 12
    assert debit_line.debit == Decimal("200.00")
    assert credit_line.account_id == 16
    assert credit_line.credit == Decimal("200.00")


def test_allocate_credit_note_to_invoice():
    db = _session()
    inv_repo = SqlAlchemyInvoiceRepository(db)
    cn_repo = SqlAlchemyCreditNoteRepository(db)

    # 1. Create and post an invoice for $1000
    inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-100",
            issue_date=date(2026, 1, 10),
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
            tax_amount=Decimal("0.00"),
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

    # 2. Create and post credit note for $400
    cn = cn_repo.create(
        CreateCreditNoteCommand(
            company_id=1,
            partner_id=1,
            note_type="customer_credit_note",
            credit_note_no="CN-100",
            issue_date=date(2026, 1, 15),
            currency="USD",
            lines=[
                CreateCreditNoteLineCommand(
                    description="Discount",
                    quantity=Decimal("1"),
                    unit_price=Decimal("400.00"),
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

    # 3. Allocate $400 to invoice
    allocated_cn = cn_repo.allocate(
        AllocateCreditNoteCommand(
            credit_note_id=cn.id,
            allocations=[CreateCreditNoteAllocationCommand(invoice_id=inv.id, amount=Decimal("400.00"))],
        )
    )
    assert allocated_cn.allocated_amount == Decimal("400.00")
    assert allocated_cn.unallocated_amount == Decimal("0.00")

    # 4. Verify invoice residual amount and credited amount
    updated_inv = inv_repo.get_by_id(inv.id)
    assert updated_inv.credited_amount == Decimal("400.00")
    assert updated_inv.residual_amount == Decimal("600.00")
    assert updated_inv.payment_status == "partially_paid"


def test_allocation_validation_guards():
    db = _session()
    inv_repo = SqlAlchemyInvoiceRepository(db)
    cn_repo = SqlAlchemyCreditNoteRepository(db)

    # Invoice for $200
    inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-200",
            issue_date=date(2026, 1, 10),
            due_date=date(2026, 1, 20),
            currency="USD",
            lines=[
                CreateInvoiceLineCommand(
                    description="Item",
                    quantity=Decimal("2"),
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

    # Credit note for $500
    cn = cn_repo.create(
        CreateCreditNoteCommand(
            company_id=1,
            partner_id=1,
            note_type="customer_credit_note",
            credit_note_no="CN-500",
            issue_date=date(2026, 1, 15),
            currency="USD",
            lines=[
                CreateCreditNoteLineCommand(
                    description="Large Credit",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
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

    # Cannot allocate more than invoice residual ($200)
    with pytest.raises(ValueError, match="exceeds remaining balance"):
        cn_repo.allocate(
            AllocateCreditNoteCommand(
                credit_note_id=cn.id,
                allocations=[CreateCreditNoteAllocationCommand(invoice_id=inv.id, amount=Decimal("300.00"))],
            )
        )

    # Cannot allocate to draft credit note
    draft_cn = cn_repo.create(
        CreateCreditNoteCommand(
            company_id=1,
            partner_id=1,
            note_type="customer_credit_note",
            credit_note_no="CN-DRAFT",
            issue_date=date(2026, 1, 15),
            currency="USD",
            lines=[
                CreateCreditNoteLineCommand(
                    description="Draft Credit",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                    account_id=14,
                )
            ],
        )
    )
    with pytest.raises(ValueError, match="Only posted credit notes can be allocated"):
        cn_repo.allocate(
            AllocateCreditNoteCommand(
                credit_note_id=draft_cn.id,
                allocations=[CreateCreditNoteAllocationCommand(invoice_id=inv.id, amount=Decimal("50.00"))],
            )
        )


def test_currency_isolation_guard():
    db = _session()
    cn_repo = SqlAlchemyCreditNoteRepository(db)

    # Attempt to create credit note with currency mismatch against partner (Partner 3 is EUR, note is USD)
    with pytest.raises(ValueError, match="does not match"):
        cn_repo.create(
            CreateCreditNoteCommand(
                company_id=1,
                partner_id=3,  # EUR partner
                note_type="customer_credit_note",
                credit_note_no="CN-EUR-USD",
                issue_date=date(2026, 1, 15),
                currency="USD",  # mismatch
                lines=[
                    CreateCreditNoteLineCommand(
                        description="Test",
                        quantity=Decimal("1"),
                        unit_price=Decimal("100.00"),
                        account_id=14,
                    )
                ],
            )
        )
