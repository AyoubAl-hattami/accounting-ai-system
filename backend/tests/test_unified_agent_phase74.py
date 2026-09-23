from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.credit_note import (
    CreditNote,
    CreditNoteAllocation,
    CreditNoteLine,
)
from app.modules.accounting.models.invoice import Invoice, InvoiceLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import Payment, PaymentAllocation
from app.modules.accounting.models.refund import Refund
from app.modules.accounting.services.accounting_tool_registry import (
    AccountingToolRegistry,
    tool_get_credit_note_details,
    tool_get_credit_notes,
    tool_get_invoice_details,
    tool_get_refunds,
    tool_propose_credit_note,
)


def test_phase74_tools_rbac_declarations():
    viewer_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("viewer")]
    assert "get_credit_notes" in viewer_tools
    assert "get_credit_note_details" in viewer_tools
    assert "get_refunds" in viewer_tools
    assert "propose_credit_note" not in viewer_tools

    accountant_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("accountant")]
    assert "get_credit_notes" in accountant_tools
    assert "get_credit_note_details" in accountant_tools
    assert "get_refunds" in accountant_tools
    assert "propose_credit_note" in accountant_tools

    admin_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("admin")]
    assert "propose_credit_note" in admin_tools


def test_propose_credit_note_creates_mutation_proposal_without_db_mutation():
    mock_db = MagicMock()
    mock_partner = MagicMock()
    mock_partner.id = 1
    mock_partner.name = "Customer Alpha"
    mock_partner.currency = "USD"

    mock_db.scalar.return_value = mock_partner

    res = tool_propose_credit_note(
        db=mock_db,
        company_id=1,
        partner_id=1,
        note_type="customer_credit_note",
        credit_note_no="CN-PROP-001",
        amount=200.0,
        description="Return item",
        issue_date="2026-01-20",
        account_code_or_name="Sales Returns",
    )

    assert res.is_mutation_proposal is True
    assert res.suggested_action is not None
    assert res.suggested_action.type == "create_credit_note"
    assert res.suggested_action.requires_confirmation is True
    assert "Credit/Debit Note creation proposed" in res.data["proposal"]
    assert res.data["details"]["amount"] == 200.0
    # Crucial: No DB mutation / commit
    assert not mock_db.commit.called
    assert not mock_db.add.called


def _in_memory_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        Company.__table__,
        Account.__table__,
        Partner.__table__,
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
    session.add(Company(id=1, name="Acme Corp", base_currency="USD", is_active=True))
    session.add(
        Partner(
            id=1,
            company_id=1,
            name="Customer Alpha",
            code="CUST01",
            is_customer=True,
            is_vendor=False,
            currency="USD",
        )
    )
    session.add(
        Account(
            id=10,
            company_id=1,
            code="1010",
            name="Bank USD",
            account_type="asset",
            currency="USD",
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
        )
    )
    session.commit()
    return session


def test_get_invoice_details_includes_credited_amount_and_allocations():
    db = _in_memory_db()

    # 1. Invoice
    inv = Invoice(
        id=1,
        company_id=1,
        partner_id=1,
        invoice_type="out_invoice",
        invoice_no="INV-2026-001",
        issue_date=date(2026, 1, 10),
        due_date=date(2026, 1, 20),
        currency="USD",
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("1000.00"),
        status="posted",
    )
    db.add(inv)
    db.flush()

    db.add(
        InvoiceLine(
            id=1,
            invoice_id=inv.id,
            line_no=1,
            description="Service",
            quantity=Decimal("10"),
            unit_price=Decimal("100.00"),
            subtotal=Decimal("1000.00"),
            account_id=14,
        )
    )

    # 2. Credit Note with Allocation
    cn = CreditNote(
        id=1,
        company_id=1,
        partner_id=1,
        note_type="customer_credit_note",
        credit_note_no="CN-001",
        issue_date=date(2026, 1, 15),
        currency="USD",
        status="posted",
        subtotal=Decimal("300.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("300.00"),
    )
    db.add(cn)
    db.flush()

    db.add(
        CreditNoteAllocation(
            id=1,
            company_id=1,
            credit_note_id=cn.id,
            invoice_id=inv.id,
            amount=Decimal("300.00"),
        )
    )
    db.commit()

    # Query get_invoice_details tool
    res = tool_get_invoice_details(db, company_id=1, invoice_id=1)
    assert "error" not in res
    assert res["invoice_number"] == "INV-2026-001"
    assert res["total_amount"] == 1000.0
    assert res["credited_amount"] == 300.0
    assert res["outstanding_amount"] == 700.0
    assert len(res["credit_allocations"]) == 1
    assert res["credit_allocations"][0]["credit_note_id"] == cn.id
    assert res["credit_allocations"][0]["allocated_amount"] == 300.0


def test_get_credit_notes_and_details():
    db = _in_memory_db()

    cn = CreditNote(
        id=1,
        company_id=1,
        partner_id=1,
        note_type="customer_credit_note",
        credit_note_no="CN-001",
        issue_date=date(2026, 1, 15),
        currency="USD",
        status="posted",
        subtotal=Decimal("300.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("300.00"),
        reason="Damaged box",
    )
    db.add(cn)
    db.flush()

    db.add(
        CreditNoteLine(
            id=1,
            credit_note_id=cn.id,
            line_no=1,
            description="Damaged item",
            quantity=Decimal("1"),
            unit_price=Decimal("300.00"),
            subtotal=Decimal("300.00"),
            account_id=14,
        )
    )
    db.commit()

    # List credit notes
    list_res = tool_get_credit_notes(db, company_id=1, partner_id=1)
    assert len(list_res) == 1
    assert list_res[0]["credit_note_no"] == "CN-001"

    # Get details
    detail_res = tool_get_credit_note_details(db, company_id=1, credit_note_id=1)
    assert "error" not in detail_res
    assert detail_res["credit_note_no"] == "CN-001"
    assert detail_res["reason"] == "Damaged box"
    assert len(detail_res["lines"]) == 1
    assert detail_res["lines"][0]["description"] == "Damaged item"


def test_get_refunds():
    db = _in_memory_db()

    ref = Refund(
        id=1,
        company_id=1,
        partner_id=1,
        refund_type="customer_refund",
        currency_code="USD",
        amount=Decimal("150.00"),
        refund_date=date(2026, 1, 20),
        bank_or_cash_account_id=10,
        receivable_or_payable_account_id=11,
        status="posted",
        reference="REF-001",
        memo="Wire transfer refund",
    )
    db.add(ref)
    db.commit()

    res = tool_get_refunds(db, company_id=1, partner_id=1)
    assert len(res) == 1
    assert res[0]["amount"] == 150.0
    assert res[0]["reference"] == "REF-001"
