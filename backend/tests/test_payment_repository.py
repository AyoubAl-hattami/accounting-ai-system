from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    CreateInvoiceLineCommand,
    PostInvoiceCommand,
)
from app.application.payments.dto import (
    CreatePaymentAllocationCommand,
    CreatePaymentCommand,
    PaymentQuery,
    PostPaymentCommand,
    VoidPaymentCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.invoice_repository import (
    SqlAlchemyInvoiceRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.payment_repository import (
    SqlAlchemyPaymentRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.credit_note import CreditNote, CreditNoteAllocation
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
        Payment.__table__,
        PaymentAllocation.__table__,
        CreditNote.__table__,
        CreditNoteAllocation.__table__,
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

    # Accounts for Company 1 (USD)
    session.add(
        Account(
            id=10,
            company_id=1,
            code="1010",
            name="Bank Account USD",
            account_type="asset",
            account_subtype="bank",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=11,
            company_id=1,
            code="1200",
            name="Accounts Receivable USD",
            account_type="asset",
            account_subtype="receivable",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=12,
            company_id=1,
            code="2100",
            name="Accounts Payable USD",
            account_type="liability",
            account_subtype="payable",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=13,
            company_id=1,
            code="4100",
            name="Sales Revenue USD",
            account_type="income",
            account_subtype="revenue",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=14,
            company_id=1,
            code="5100",
            name="Office Expense USD",
            account_type="expense",
            account_subtype="expense",
            currency="USD",
            is_active=True,
        )
    )

    # EUR Accounts for Company 1
    session.add(
        Account(
            id=20,
            company_id=1,
            code="1020",
            name="Bank Account EUR",
            account_type="asset",
            account_subtype="bank",
            currency="EUR",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=21,
            company_id=1,
            code="1220",
            name="Accounts Receivable EUR",
            account_type="asset",
            account_subtype="receivable",
            currency="EUR",
            is_active=True,
        )
    )

    # Accounts for Company 2
    session.add(
        Account(
            id=30,
            company_id=2,
            code="1010",
            name="Co2 Bank",
            account_type="asset",
            account_subtype="bank",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=31,
            company_id=2,
            code="1200",
            name="Co2 AR",
            account_type="asset",
            account_subtype="receivable",
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
            code="CUST-001",
            is_customer=True,
            currency="USD",
            receivable_account_id=11,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=2,
            company_id=1,
            name="Customer Beta",
            code="CUST-002",
            is_customer=True,
            currency="USD",
            receivable_account_id=11,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=3,
            company_id=1,
            name="Vendor Gamma",
            code="VEND-001",
            is_vendor=True,
            currency="USD",
            payable_account_id=12,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=4,
            company_id=1,
            name="Customer EUR",
            code="CUST-EUR",
            is_customer=True,
            currency="EUR",
            receivable_account_id=21,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=5,
            company_id=2,
            name="Co2 Customer",
            code="CUST-CO2",
            is_customer=True,
            currency="USD",
            receivable_account_id=31,
            is_active=True,
        )
    )

    session.flush()
    return session


def _create_and_post_invoice(
    session: Session,
    company_id: int,
    partner_id: int,
    invoice_type: str,
    invoice_no: str,
    currency: str,
    amount: Decimal,
    account_id: int,
    ar_ap_account_id: int,
) -> int:
    inv_repo = SqlAlchemyInvoiceRepository(session)
    inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=company_id,
            partner_id=partner_id,
            invoice_type=invoice_type,
            invoice_no=invoice_no,
            issue_date=date(2026, 1, 10),
            due_date=date(2026, 1, 25),
            currency=currency,
            lines=[
                CreateInvoiceLineCommand(
                    description="Services",
                    quantity=Decimal("1.0000"),
                    unit_price=amount,
                    account_id=account_id,
                )
            ],
        )
    )
    posted = inv_repo.post(
        PostInvoiceCommand(
            invoice_id=inv.id,
            receivable_or_payable_account_id=ar_ap_account_id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    return posted.id


def test_payments_comprehensive_workflow():
    session = _session()
    inv_repo = SqlAlchemyInvoiceRepository(session)
    pay_repo = SqlAlchemyPaymentRepository(session)

    # 1. Create a 1,000 USD sales invoice for Customer Alpha
    inv1_id = _create_and_post_invoice(
        session=session,
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-1001",
        currency="USD",
        amount=Decimal("1000.00"),
        account_id=13,
        ar_ap_account_id=11,
    )

    # Verify initial invoice state
    inv1 = inv_repo.get_by_id(inv1_id)
    assert inv1.total_amount == Decimal("1000.00")
    assert inv1.paid_amount == Decimal("0.00")
    assert inv1.residual_amount == Decimal("1000.00")
    assert inv1.payment_status == "unpaid"

    # 2. Scenario 2: Partial customer payment (400 USD)
    pay1 = pay_repo.create(
        CreatePaymentCommand(
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("400.00"),
            payment_date=date(2026, 1, 15),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=11,
            allocations=[
                CreatePaymentAllocationCommand(
                    invoice_id=inv1_id,
                    amount=Decimal("400.00"),
                )
            ],
        )
    )
    assert pay1.status == "draft"
    assert pay1.allocated_amount == Decimal("400.00")
    assert pay1.unallocated_amount == Decimal("0.00")

    # Post partial payment
    pay1_posted = pay_repo.post(
        PostPaymentCommand(
            payment_id=pay1.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    assert pay1_posted.status == "posted"
    assert pay1_posted.journal_entry_id is not None

    # Check GL Entry: Debit Bank 400, Credit AR 400
    entry1 = session.get(JournalEntry, pay1_posted.journal_entry_id)
    assert entry1 is not None
    assert len(entry1.lines) == 2
    # 11. GL debit = credit
    assert sum(l.debit for l in entry1.lines) == Decimal("400.00")
    assert sum(l.credit for l in entry1.lines) == Decimal("400.00")
    assert entry1.lines[0].account_id == 10  # Bank
    assert entry1.lines[0].debit == Decimal("400.00")
    assert entry1.lines[1].account_id == 11  # AR
    assert entry1.lines[1].credit == Decimal("400.00")

    # 10. Recalculation: Invoice is partially paid (400 paid, 600 due)
    inv1_after_pay1 = inv_repo.get_by_id(inv1_id)
    assert inv1_after_pay1.paid_amount == Decimal("400.00")
    assert inv1_after_pay1.residual_amount == Decimal("600.00")
    assert inv1_after_pay1.payment_status == "partially_paid"

    # 3. Scenario 3: Multiple payments against one invoice (Second payment 600 USD)
    pay2 = pay_repo.create(
        CreatePaymentCommand(
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("600.00"),
            payment_date=date(2026, 1, 20),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=11,
            allocations=[
                CreatePaymentAllocationCommand(
                    invoice_id=inv1_id,
                    amount=Decimal("600.00"),
                )
            ],
        )
    )
    pay2_posted = pay_repo.post(
        PostPaymentCommand(
            payment_id=pay2.id,
            fiscal_year_id=1,
            fiscal_period_id=1,
        )
    )
    assert pay2_posted.status == "posted"

    # 1. Scenario 1: Full customer payment -> Invoice is now paid (1000 paid, 0 due)
    inv1_after_pay2 = inv_repo.get_by_id(inv1_id)
    assert inv1_after_pay2.paid_amount == Decimal("1000.00")
    assert inv1_after_pay2.residual_amount == Decimal("0.00")
    assert inv1_after_pay2.payment_status == "paid"
    assert inv1_after_pay2.status == "paid"

    # 8. Scenario 8: Duplicate posting protection
    with pytest.raises(ValueError, match="Cannot post payment in status 'posted'"):
        pay_repo.post(
            PostPaymentCommand(
                payment_id=pay2.id,
                fiscal_year_id=1,
                fiscal_period_id=1,
            )
        )

    # 9. Scenario 9: Void payment (Void second payment of 600 USD)
    pay2_voided = pay_repo.void(VoidPaymentCommand(payment_id=pay2.id))
    assert pay2_voided.status == "void"
    entry2 = session.get(JournalEntry, pay2_posted.journal_entry_id)
    assert entry2 is not None
    assert entry2.status == "void"

    # Invoice reverts back to partially_paid (400 paid, 600 due)
    inv1_after_void = inv_repo.get_by_id(inv1_id)
    assert inv1_after_void.paid_amount == Decimal("400.00")
    assert inv1_after_void.residual_amount == Decimal("600.00")
    assert inv1_after_void.payment_status == "partially_paid"
    assert inv1_after_void.status == "posted"


def test_one_payment_multiple_invoices_and_vendor_payment():
    session = _session()
    inv_repo = SqlAlchemyInvoiceRepository(session)
    pay_repo = SqlAlchemyPaymentRepository(session)

    # 4. Scenario 4: One payment against multiple invoices
    invA_id = _create_and_post_invoice(
        session=session,
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-A",
        currency="USD",
        amount=Decimal("300.00"),
        account_id=13,
        ar_ap_account_id=11,
    )
    invB_id = _create_and_post_invoice(
        session=session,
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-B",
        currency="USD",
        amount=Decimal("500.00"),
        account_id=13,
        ar_ap_account_id=11,
    )

    pay_multi = pay_repo.create(
        CreatePaymentCommand(
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("800.00"),
            payment_date=date(2026, 1, 18),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=11,
            allocations=[
                CreatePaymentAllocationCommand(invoice_id=invA_id, amount=Decimal("300.00")),
                CreatePaymentAllocationCommand(invoice_id=invB_id, amount=Decimal("500.00")),
            ],
        )
    )
    pay_repo.post(
        PostPaymentCommand(payment_id=pay_multi.id, fiscal_year_id=1, fiscal_period_id=1)
    )

    invA = inv_repo.get_by_id(invA_id)
    invB = inv_repo.get_by_id(invB_id)
    assert invA.payment_status == "paid" and invA.residual_amount == Decimal("0.00")
    assert invB.payment_status == "paid" and invB.residual_amount == Decimal("0.00")

    # 5. Scenario 5: Vendor payment
    bill_id = _create_and_post_invoice(
        session=session,
        company_id=1,
        partner_id=3,  # Vendor Gamma
        invoice_type="in_invoice",
        invoice_no="BILL-V1",
        currency="USD",
        amount=Decimal("500.00"),
        account_id=14,
        ar_ap_account_id=12,
    )

    vendor_pay = pay_repo.create(
        CreatePaymentCommand(
            company_id=1,
            partner_id=3,
            payment_type="vendor_payment",
            currency_code="USD",
            amount=Decimal("500.00"),
            payment_date=date(2026, 1, 22),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=12,
            allocations=[
                CreatePaymentAllocationCommand(invoice_id=bill_id, amount=Decimal("500.00"))
            ],
        )
    )
    posted_vendor_pay = pay_repo.post(
        PostPaymentCommand(payment_id=vendor_pay.id, fiscal_year_id=1, fiscal_period_id=1)
    )

    # Check GL Entry: Debit AP 500, Credit Bank 500
    ventry = session.get(JournalEntry, posted_vendor_pay.journal_entry_id)
    assert ventry.lines[0].account_id == 12  # AP
    assert ventry.lines[0].debit == Decimal("500.00")
    assert ventry.lines[1].account_id == 10  # Bank
    assert ventry.lines[1].credit == Decimal("500.00")

    bill = inv_repo.get_by_id(bill_id)
    assert bill.payment_status == "paid"
    assert bill.residual_amount == Decimal("0.00")


def test_payment_guards_and_failures():
    session = _session()
    inv_repo = SqlAlchemyInvoiceRepository(session)
    pay_repo = SqlAlchemyPaymentRepository(session)

    inv_id = _create_and_post_invoice(
        session=session,
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-G1",
        currency="USD",
        amount=Decimal("500.00"),
        account_id=13,
        ar_ap_account_id=11,
    )

    # 6. Scenario 6: Over-allocation rejection (allocating 600 to 500 invoice)
    with pytest.raises(ValueError, match="exceeds invoice .* remaining balance"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=1,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("600.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
                allocations=[
                    CreatePaymentAllocationCommand(invoice_id=inv_id, amount=Decimal("600.00"))
                ],
            )
        )

    # Also over-allocation where total allocations exceed payment amount
    with pytest.raises(ValueError, match="Total allocated amount .* cannot exceed payment amount"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=1,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("300.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
                allocations=[
                    CreatePaymentAllocationCommand(invoice_id=inv_id, amount=Decimal("400.00"))
                ],
            )
        )

    # 7. Scenario 7: Currency mismatch rejection
    # A. Bank account EUR vs Payment USD
    with pytest.raises(ValueError, match="Bank/Cash account currency 'EUR' does not match"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=1,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=20,  # EUR Bank
                receivable_or_payable_account_id=11,
            )
        )

    # B. AR account EUR vs Payment USD
    with pytest.raises(ValueError, match="Receivable/Payable account currency 'EUR' does not match"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=1,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=21,  # EUR AR
            )
        )

    # C. EUR Partner vs Payment USD
    with pytest.raises(ValueError, match="Partner currency 'EUR' does not match"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=4,  # EUR Partner
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
            )
        )

    # 13. Scenario 13: Allocation to invoice belonging to another partner must fail
    with pytest.raises(ValueError, match="does not belong to the selected partner"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=2,  # Customer Beta
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
                allocations=[
                    CreatePaymentAllocationCommand(invoice_id=inv_id, amount=Decimal("100.00"))
                ],
            )
        )

    # 14. Scenario 14: Allocation to invoice belonging to another company must fail
    with pytest.raises(ValueError, match="belongs to another company"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=2,  # Other Corp
                partner_id=5,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=30,
                receivable_or_payable_account_id=31,
                allocations=[
                    CreatePaymentAllocationCommand(invoice_id=inv_id, amount=Decimal("100.00"))
                ],
            )
        )

    # 15. Scenario 15: Payment against void/draft invoice must fail
    draft_inv = inv_repo.create(
        CreateInvoiceCommand(
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-DRAFT",
            issue_date=date(2026, 1, 10),
            due_date=date(2026, 1, 25),
            currency="USD",
            lines=[
                CreateInvoiceLineCommand(
                    description="Services",
                    quantity=Decimal("1.0000"),
                    unit_price=Decimal("200.00"),
                    account_id=13,
                )
            ],
        )
    )
    with pytest.raises(ValueError, match="Cannot allocate payment to invoice .* in status 'draft'"):
        pay_repo.create(
            CreatePaymentCommand(
                company_id=1,
                partner_id=1,
                payment_type="customer_receipt",
                currency_code="USD",
                amount=Decimal("100.00"),
                payment_date=date(2026, 1, 15),
                bank_or_cash_account_id=10,
                receivable_or_payable_account_id=11,
                allocations=[
                    CreatePaymentAllocationCommand(
                        invoice_id=draft_inv.id, amount=Decimal("100.00")
                    )
                ],
            )
        )

    # 12. Scenario 12: Company isolation
    valid_pay = pay_repo.create(
        CreatePaymentCommand(
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("100.00"),
            payment_date=date(2026, 1, 15),
            bank_or_cash_account_id=10,
            receivable_or_payable_account_id=11,
        )
    )
    co2_list = pay_repo.list(PaymentQuery(company_id=2))
    assert len(co2_list.items) == 0
    co1_list = pay_repo.list(PaymentQuery(company_id=1))
    assert any(p.id == valid_pay.id for p in co1_list.items)
