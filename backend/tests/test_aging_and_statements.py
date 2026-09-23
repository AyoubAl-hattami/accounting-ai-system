from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.reports.aging_dto import AgingQuery
from app.application.reports.statement_dto import PartnerStatementQuery
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
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
    ):
        table.create(bind=engine)

    session = Session(engine)
    session.add(Company(id=1, name="Acme Inc", base_currency="USD", is_active=True))
    session.add(Company(id=2, name="Beta Corp", base_currency="USD", is_active=True))

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

    # Accounts
    session.add(
        Account(
            id=1,
            company_id=1,
            code="1100",
            name="Cash",
            account_type="asset",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=2,
            company_id=1,
            code="1200",
            name="Accounts Receivable",
            account_type="asset",
            currency="USD",
            is_active=True,
        )
    )
    session.add(
        Account(
            id=3,
            company_id=1,
            code="2200",
            name="Accounts Payable",
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
            code="CUST-001",
            name="Customer Alpha",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            receivable_account_id=2,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=2,
            company_id=1,
            code="VEND-001",
            name="Vendor Beta",
            is_customer=False,
            is_vendor=True,
            currency="USD",
            payable_account_id=3,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=3,
            company_id=1,
            code="CUST-EUR",
            name="Euro Customer",
            is_customer=True,
            is_vendor=False,
            currency="EUR",
            receivable_account_id=2,
            is_active=True,
        )
    )
    session.add(
        Partner(
            id=4,
            company_id=2,
            code="CUST-COMP2",
            name="Company 2 Customer",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            receivable_account_id=2,
            is_active=True,
        )
    )

    session.commit()
    return session


# 1. Current invoice (due_date on or after as_of_date)
def test_aging_bucket_current():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-001",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 20), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "current"
    assert report.items[0].days_overdue == -11
    assert report.totals.total_current == Decimal("1000.00")
    assert report.totals.total_outstanding == Decimal("1000.00")


# 2. 1–30 overdue invoice
def test_aging_bucket_1_30():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-002",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 15),
            currency="USD",
            status="posted",
            total_amount=Decimal("500.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 30), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "1-30"
    assert report.items[0].days_overdue == 15
    assert report.totals.total_1_30 == Decimal("500.00")


# 3. 31–60 overdue invoice
def test_aging_bucket_31_60():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-003",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 15),
            currency="USD",
            status="posted",
            total_amount=Decimal("700.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 3, 1), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "31-60"
    assert report.items[0].days_overdue == 45
    assert report.totals.total_31_60 == Decimal("700.00")


# 4. 61–90 overdue invoice
def test_aging_bucket_61_90():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-004",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 15),
            currency="USD",
            status="posted",
            total_amount=Decimal("800.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 4, 1), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "61-90"
    assert report.items[0].days_overdue == 76
    assert report.totals.total_61_90 == Decimal("800.00")


# 5. 91–120 overdue invoice
def test_aging_bucket_91_120():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-005",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 15),
            currency="USD",
            status="posted",
            total_amount=Decimal("900.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 4, 30), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "91-120"
    assert report.items[0].days_overdue == 105
    assert report.totals.total_91_120 == Decimal("900.00")


# 6. 120+ overdue invoice
def test_aging_bucket_120_plus():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-006",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 15),
            currency="USD",
            status="posted",
            total_amount=Decimal("1200.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 6, 1), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].bucket == "120+"
    assert report.items[0].days_overdue == 137
    assert report.totals.total_120_plus == Decimal("1200.00")


# 7. Partially paid invoice
def test_aging_partially_paid():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-PARTIAL",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("400.00"),
            payment_date=date(2026, 1, 15),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=1,
            invoice_id=1,
            amount=Decimal("400.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 31), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].original_amount == Decimal("1000.00")
    assert report.items[0].paid_amount == Decimal("400.00")
    assert report.items[0].outstanding_amount == Decimal("600.00")
    assert report.totals.total_outstanding == Decimal("600.00")


# 8. Fully paid invoice excluded
def test_aging_fully_paid_excluded():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-FULL",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="paid",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("1000.00"),
            payment_date=date(2026, 1, 15),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=1,
            invoice_id=1,
            amount=Decimal("1000.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 31), currency="USD")
    )
    assert len(report.items) == 0
    assert report.totals.total_outstanding == Decimal("0.00")


# 9. Void invoice excluded
def test_aging_void_invoice_excluded():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-VOID",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="void",
            total_amount=Decimal("1000.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 31), currency="USD")
    )
    assert len(report.items) == 0


# 10. Draft invoice excluded
def test_aging_draft_invoice_excluded():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-DRAFT",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="draft",
            total_amount=Decimal("1000.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 31), currency="USD")
    )
    assert len(report.items) == 0


# 11. Payment after as_of_date must not affect historical aging
def test_payment_after_as_of_date_ignored():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-HIST",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    # Payment made on 2026-02-10
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("400.00"),
            payment_date=date(2026, 2, 10),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=1,
            invoice_id=1,
            amount=Decimal("400.00"),
        )
    )
    db.commit()

    # Query as of 2026-02-05 (before payment): outstanding should still be 1000.00
    report_before = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 5), currency="USD")
    )
    assert len(report_before.items) == 1
    assert report_before.items[0].paid_amount == Decimal("0.00")
    assert report_before.items[0].outstanding_amount == Decimal("1000.00")


# 12. Payment before as_of_date must affect balance
def test_payment_before_as_of_date_affects_balance():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-HIST2",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("400.00"),
            payment_date=date(2026, 2, 10),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=1,
            invoice_id=1,
            amount=Decimal("400.00"),
        )
    )
    db.commit()

    # Query as of 2026-02-20 (after payment): outstanding should be 600.00
    report_after = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 20), currency="USD")
    )
    assert len(report_after.items) == 1
    assert report_after.items[0].paid_amount == Decimal("400.00")
    assert report_after.items[0].outstanding_amount == Decimal("600.00")
    assert report_after.items[0].bucket == "1-30"  # 20 days overdue


# 13. AR aging
def test_ar_aging_filters_only_out_invoices():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-AR",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=2,
            invoice_type="in_invoice",
            invoice_no="BILL-AP",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("500.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].invoice_no == "INV-AR"


# 14. AP aging
def test_ap_aging_filters_only_in_invoices():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-AR",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=2,
            invoice_type="in_invoice",
            invoice_no="BILL-AP",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("500.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ap", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].invoice_no == "BILL-AP"


# 15. Multiple partners
def test_aging_multiple_partners():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Partner(
            id=5,
            company_id=1,
            code="CUST-002",
            name="Customer Beta",
            is_customer=True,
            is_vendor=False,
            currency="USD",
            receivable_account_id=2,
            is_active=True,
        )
    )
    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-P1",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=5,
            invoice_type="out_invoice",
            invoice_no="INV-P2",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("2000.00"),
        )
    )
    db.commit()

    # Filter all
    all_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(all_report.items) == 2
    assert all_report.totals.total_outstanding == Decimal("3000.00")

    # Filter partner 1 only
    p1_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD", partner_id=1)
    )
    assert len(p1_report.items) == 1
    assert p1_report.items[0].partner_id == 1


# 16. Multiple currencies
def test_aging_multiple_currencies_isolated():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-USD",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=3,
            invoice_type="out_invoice",
            invoice_no="INV-EUR",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="EUR",
            status="posted",
            total_amount=Decimal("2000.00"),
        )
    )
    db.commit()

    usd_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(usd_report.items) == 1
    assert usd_report.items[0].currency == "USD"
    assert usd_report.totals.total_outstanding == Decimal("1000.00")

    eur_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="EUR")
    )
    assert len(eur_report.items) == 1
    assert eur_report.items[0].currency == "EUR"
    assert eur_report.totals.total_outstanding == Decimal("2000.00")


# 17. Currency totals must never mix
def test_currency_totals_never_mixed():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-USD-1",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("100.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=3,
            invoice_type="out_invoice",
            invoice_no="INV-EUR-1",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="EUR",
            status="posted",
            total_amount=Decimal("200.00"),
        )
    )
    db.commit()

    usd_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert usd_report.totals.total_outstanding == Decimal("100.00")
    assert not any(item.currency == "EUR" for item in usd_report.items)


# 18. Company isolation
def test_company_isolation():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-COMP1",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Invoice(
            id=2,
            company_id=2,
            partner_id=4,
            invoice_type="out_invoice",
            invoice_no="INV-COMP2",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("2000.00"),
        )
    )
    db.commit()

    c1_report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(c1_report.items) == 1
    assert c1_report.items[0].invoice_no == "INV-COMP1"

    c2_report = repo.get_aging_report(
        AgingQuery(company_id=2, report_type="ar", as_of_date=date(2026, 2, 1), currency="USD")
    )
    assert len(c2_report.items) == 1
    assert c2_report.items[0].invoice_no == "INV-COMP2"


# 19. Partner statement opening balance
def test_partner_statement_opening_balance():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    # Invoices and payments before 2026-02-01
    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-JAN",
            issue_date=date(2026, 1, 10),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1500.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("500.00"),
            payment_date=date(2026, 1, 25),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
        )
    )
    # Opening balance should be 1500 - 500 = 1000.00
    assert statement.opening_balance == Decimal("1000.00")
    assert statement.closing_balance == Decimal("1000.00")
    assert len(statement.transactions) == 0


# 20. Partner statement running balance
def test_partner_statement_running_balance():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-1",
            issue_date=date(2026, 2, 5),
            due_date=date(2026, 2, 28),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("300.00"),
            payment_date=date(2026, 2, 15),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
        )
    )
    assert statement.opening_balance == Decimal("0.00")
    assert len(statement.transactions) == 2
    # First transaction (invoice): debit = 1000, running = 1000
    assert statement.transactions[0].debit == Decimal("1000.00")
    assert statement.transactions[0].running_balance == Decimal("1000.00")
    # Second transaction (payment): credit = 300, running = 700
    assert statement.transactions[1].credit == Decimal("300.00")
    assert statement.transactions[1].running_balance == Decimal("700.00")
    assert statement.closing_balance == Decimal("700.00")


# 21. Customer receipt reflected correctly
def test_customer_receipt_reflected_correctly():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-CUST",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("500.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("500.00"),
            payment_date=date(2026, 1, 10),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
    )
    assert statement.total_debit == Decimal("500.00")
    assert statement.total_credit == Decimal("500.00")
    assert statement.closing_balance == Decimal("0.00")


# 22. Vendor payment reflected correctly
def test_vendor_payment_reflected_correctly():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    # Vendor bill: 800.00 (credit to vendor)
    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=2,
            invoice_type="in_invoice",
            invoice_no="BILL-VEND",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("800.00"),
        )
    )
    # Vendor payment: 300.00 (debit to vendor, reduces payable)
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=2,
            payment_type="vendor_payment",
            currency_code="USD",
            amount=Decimal("300.00"),
            payment_date=date(2026, 1, 15),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=3,
            status="posted",
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=2,
            currency="USD",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
    )
    assert statement.total_credit == Decimal("800.00")
    assert statement.total_debit == Decimal("300.00")
    assert statement.closing_balance == Decimal("500.00")  # We still owe 500.00


# 23. Date range filtering
def test_statement_date_range_filtering():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    # Before range
    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-PRE",
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("100.00"),
        )
    )
    # Inside range
    db.add(
        Invoice(
            id=2,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-MID",
            issue_date=date(2026, 2, 15),
            due_date=date(2026, 2, 28),
            currency="USD",
            status="posted",
            total_amount=Decimal("200.00"),
        )
    )
    # After range
    db.add(
        Invoice(
            id=3,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-POST",
            issue_date=date(2026, 3, 15),
            due_date=date(2026, 3, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("300.00"),
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
        )
    )
    assert statement.opening_balance == Decimal("100.00")
    assert len(statement.transactions) == 1
    assert statement.transactions[0].document_no == "INV-MID"
    assert statement.closing_balance == Decimal("300.00")


# 24. Void payment excluded
def test_statement_void_payment_excluded():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-V1",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("500.00"),
        )
    )
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("500.00"),
            payment_date=date(2026, 1, 10),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="void",
        )
    )
    db.commit()

    statement = repo.get_partner_statement(
        PartnerStatementQuery(
            company_id=1,
            partner_id=1,
            currency="USD",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
    )
    assert statement.total_credit == Decimal("0.00")
    assert statement.closing_balance == Decimal("500.00")


# 25. Multiple allocations against same invoice
def test_multiple_allocations_against_same_invoice():
    db = _session()
    repo = SqlAlchemyReportRepository(db)

    db.add(
        Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-MULTI-ALLOC",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            currency="USD",
            status="posted",
            total_amount=Decimal("1000.00"),
        )
    )
    # Payment 1: 300.00
    db.add(
        Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("300.00"),
            payment_date=date(2026, 1, 10),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=1,
            invoice_id=1,
            amount=Decimal("300.00"),
        )
    )
    # Payment 2: 250.00
    db.add(
        Payment(
            id=2,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("250.00"),
            payment_date=date(2026, 1, 20),
            bank_or_cash_account_id=1,
            receivable_or_payable_account_id=2,
            status="posted",
        )
    )
    db.add(
        PaymentAllocation(
            id=2,
            company_id=1,
            payment_id=2,
            invoice_id=1,
            amount=Decimal("250.00"),
        )
    )
    db.commit()

    report = repo.get_aging_report(
        AgingQuery(company_id=1, report_type="ar", as_of_date=date(2026, 1, 31), currency="USD")
    )
    assert len(report.items) == 1
    assert report.items[0].original_amount == Decimal("1000.00")
    assert report.items[0].paid_amount == Decimal("550.00")
    assert report.items[0].outstanding_amount == Decimal("450.00")
    assert report.totals.total_outstanding == Decimal("450.00")
