"""Tests for Accounting Tool Registry, RBAC, tenant isolation, and proposal generation."""

from unittest.mock import MagicMock

import pytest

from app.modules.accounting.services.accounting_tool_registry import (
    AccountingToolRegistry,
    tool_propose_journal_entry,
)


def test_tool_declarations_rbac_filtering():
    viewer_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("viewer")]
    assert "get_profit_loss" in viewer_tools
    assert "get_balance_sheet" in viewer_tools
    assert "get_accounts" in viewer_tools
    assert "propose_journal_entry" not in viewer_tools
    assert "get_audit_logs" not in viewer_tools

    auditor_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("auditor")]
    assert "get_audit_logs" in auditor_tools
    assert "propose_journal_entry" not in auditor_tools

    accountant_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("accountant")]
    assert "propose_journal_entry" in accountant_tools
    assert "get_profit_loss" in accountant_tools

    admin_tools = [d.name for d in AccountingToolRegistry.get_tool_declarations_for_role("admin")]
    assert "propose_journal_entry" in admin_tools
    assert "get_audit_logs" in admin_tools


def test_execute_tool_permission_denied_for_viewer_on_propose_entry():
    mock_db = MagicMock()
    result = AccountingToolRegistry.execute_tool(
        tool_name="propose_journal_entry",
        args={"debit_account": "Cash", "credit_account": "Revenue", "amount": 100.0, "description": "Test"},
        db=mock_db,
        company_id=1,
        user_role="viewer",
    )
    assert result.error == "Access denied."
    assert "Access denied" in result.data.get("error", "")


def test_execute_tool_unknown_tool():
    mock_db = MagicMock()
    result = AccountingToolRegistry.execute_tool(
        tool_name="non_existent_tool",
        args={},
        db=mock_db,
        company_id=1,
        user_role="admin",
    )
    assert "Unknown tool" in result.error


def test_propose_journal_entry_creates_suggested_action_without_db_mutation():
    mock_db = MagicMock()
    mock_debit = MagicMock()
    mock_debit.id = 10
    mock_debit.code = "1010"
    mock_debit.name = "Cash"

    mock_credit = MagicMock()
    mock_credit.id = 20
    mock_credit.code = "4010"
    mock_credit.name = "Sales Revenue"

    # Return debit then credit
    mock_db.scalars.return_value.first.side_effect = [mock_debit, mock_credit]

    res = tool_propose_journal_entry(
        db=mock_db,
        company_id=5,
        debit_account="Cash",
        credit_account="Sales Revenue",
        amount=500.0,
        description="Cash sale",
    )

    assert res.is_mutation_proposal is True
    assert res.suggested_action is not None
    assert res.suggested_action.type == "create_journal_entry_draft"
    assert res.suggested_action.requires_confirmation is True
    assert res.data["status"] == "proposal_created"
    # Verify no commit was made to db
    assert not mock_db.commit.called


def test_get_invoice_details_regression():
    from datetime import date
    from decimal import Decimal
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.modules.accounting.models.company import Company
    from app.modules.accounting.models.account import Account
    from app.modules.accounting.models.partner import Partner
    from app.modules.accounting.models.invoice import Invoice, InvoiceLine
    from app.modules.accounting.models.payment import Payment, PaymentAllocation
    from app.modules.accounting.models.credit_note import CreditNote, CreditNoteAllocation

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        Company.__table__,
        Account.__table__,
        Partner.__table__,
        Invoice.__table__,
        InvoiceLine.__table__,
        Payment.__table__,
        PaymentAllocation.__table__,
        CreditNote.__table__,
        CreditNoteAllocation.__table__,
    ):
        table.create(bind=engine)

    with Session(engine) as session:
        company = Company(id=1, name="Test Co", base_currency="USD", is_active=True)
        session.add(company)
        acc = Account(id=1, company_id=1, code="1200", name="AR", account_type="asset", currency="USD", is_active=True)
        rev_acc = Account(id=2, company_id=1, code="4100", name="Sales", account_type="income", currency="USD", is_active=True)
        bank_acc = Account(id=3, company_id=1, code="1110", name="Bank", account_type="asset", currency="USD", is_active=True)
        session.add_all([acc, rev_acc, bank_acc])
        partner = Partner(id=1, company_id=1, code="C-1", name="Client", is_customer=True, is_vendor=False, currency="USD", is_active=True)
        session.add(partner)
        session.commit()

        inv = Invoice(
            id=1,
            company_id=1,
            partner_id=1,
            invoice_type="out_invoice",
            invoice_no="INV-REG-001",
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            currency="USD",
            status="posted",
            subtotal=Decimal("1500.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("1500.00"),
        )
        session.add(inv)
        session.commit()

        line = InvoiceLine(
            id=1,
            invoice_id=inv.id,
            line_no=1,
            description="Consulting Services (30 hrs @ 50/hr)",
            quantity=Decimal("30.0000"),
            unit_price=Decimal("50.00"),
            subtotal=Decimal("1500.00"),
            account_id=rev_acc.id,
        )
        session.add(line)

        payment = Payment(
            id=1,
            company_id=1,
            partner_id=1,
            payment_type="customer_receipt",
            currency_code="USD",
            amount=Decimal("500.00"),
            payment_date=date(2026, 2, 1),
            bank_or_cash_account_id=bank_acc.id,
            receivable_or_payable_account_id=acc.id,
            status="posted",
        )
        session.add(payment)
        session.commit()

        alloc = PaymentAllocation(
            id=1,
            company_id=1,
            payment_id=payment.id,
            invoice_id=inv.id,
            amount=Decimal("500.00"),
        )
        session.add(alloc)
        session.commit()

        # Execute get_invoice_details
        result = AccountingToolRegistry.execute_tool(
            tool_name="get_invoice_details",
            args={"invoice_number": "INV-REG-001"},
            db=session,
            company_id=1,
            user_role="admin",
        )

        assert result.error is None
        data = result.data
        assert data["invoice_number"] == "INV-REG-001"
        assert data["total_amount"] == 1500.0
        assert data["paid_amount"] == 500.0
        assert data["outstanding_amount"] == 1000.0
        assert len(data["lines"]) == 1
        assert data["lines"][0]["description"] == "Consulting Services (30 hrs @ 50/hr)"
        assert data["lines"][0]["quantity"] == 30.0
        assert data["lines"][0]["unit_price"] == 50.0
        assert data["lines"][0]["subtotal"] == 1500.0
        assert len(data["allocations"]) == 1
        assert data["allocations"][0]["allocated_amount"] == 500.0



# ── get_account_ledger ───────────────────────────────────────────────────────
#
# The tool read ledger.total_debit and ledger.total_credit, which
# AccountLedgerRead does not have, so EVERY call raised AttributeError and
# came back to the model as "Error executing get_account_ledger:
# 'AccountLedgerRead' object has no attribute 'total_debit'". It shipped that
# way and nothing noticed, because nothing called it.

from datetime import date
from decimal import Decimal

from app.application.reports.dto import AccountLedgerLine, AccountLedgerRead
from app.modules.accounting.services import accounting_tool_registry as registry


def _account(account_id=7, code="1110", name="Main Bank", currency="USD"):
    account = MagicMock()
    account.id, account.code, account.name, account.currency = account_id, code, name, currency
    return account


def _ledger(lines, total_lines=None, currency="USD"):
    return AccountLedgerRead(
        company_id=1,
        account_id=7,
        account_code="1110",
        account_name="Main Bank",
        account_type="asset",
        start_date=None,
        end_date=None,
        opening_balance=Decimal("100.00"),
        closing_balance=Decimal("400.00"),
        lines=lines,
        total_lines=total_lines if total_lines is not None else len(lines),
        currency=currency,
    )


def _line(entry_no, debit, credit, running):
    return AccountLedgerLine(
        journal_entry_id=1,
        entry_no=entry_no,
        entry_date=date(2026, 1, 5),
        line_no=1,
        description="rent",
        debit=Decimal(debit),
        credit=Decimal(credit),
        running_balance=Decimal(running),
    )


def _db_returning(account, matches=None):
    db = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = account
    scalars.all.return_value = matches or []
    db.scalars.return_value = scalars
    return db


def test_get_account_ledger_returns_a_ledger(monkeypatch):
    lines = [_line("JE-1", "300", "0", "400"), _line("JE-2", "0", "50", "350")]
    monkeypatch.setattr(registry, "get_account_ledger", lambda **kwargs: _ledger(lines))

    result = registry.tool_get_account_ledger(
        db=_db_returning(_account()), company_id=1, account_identifier="1110"
    )

    assert "error" not in result, result
    assert result["account_code"] == "1110"
    assert result["opening_balance"] == 100.0
    assert result["closing_balance"] == 400.0
    assert result["debit_of_shown_lines"] == 300.0
    assert result["credit_of_shown_lines"] == 50.0
    assert result["truncated"] is False
    assert [entry["entry_no"] for entry in result["entries"]] == ["JE-1", "JE-2"]


def test_get_account_ledger_says_when_it_is_showing_a_page(monkeypatch):
    """[D3] paginates this report, so the lines can be part of a longer window.
    Summing a page and calling it a total is how a model states a wrong figure
    with confidence."""
    lines = [_line(f"JE-{i}", "10", "0", "10") for i in range(registry._LEDGER_LINES_SHOWN + 5)]
    monkeypatch.setattr(registry, "get_account_ledger", lambda **kwargs: _ledger(lines, total_lines=500))

    result = registry.tool_get_account_ledger(
        db=_db_returning(_account()), company_id=1, account_identifier="1110"
    )

    assert result["lines_shown"] == registry._LEDGER_LINES_SHOWN
    assert result["lines_total"] == 500
    assert result["truncated"] is True
    assert "total_debit" not in result and "total_credit" not in result, (
        "A figure named like a window total must not be a page sum."
    )


def test_get_account_ledger_reports_an_unavailable_report(monkeypatch):
    monkeypatch.setattr(registry, "get_account_ledger", lambda **kwargs: None)

    result = registry.tool_get_account_ledger(
        db=_db_returning(_account()), company_id=1, account_identifier="1110"
    )

    assert "could not be produced" in result["error"]


def test_get_account_ledger_refuses_to_guess_between_accounts(monkeypatch):
    """'expense' matched five accounts and answered about one of them."""
    monkeypatch.setattr(
        registry, "get_account_ledger",
        lambda **kwargs: pytest.fail("a ledger was fetched for a guessed account"),
    )
    candidates = [
        _account(1, "5000", "Expenses"),
        _account(2, "5100", "Rent Expense"),
        _account(3, "5200", "Software Expense"),
    ]

    result = registry.tool_get_account_ledger(
        db=_db_returning(None, matches=candidates), company_id=1, account_identifier="expense"
    )

    assert "matches 3 accounts" in result["error"]
    assert [candidate["code"] for candidate in result["candidates"]] == ["5000", "5100", "5200"]


def test_get_account_ledger_takes_an_exact_code_over_a_name_match(monkeypatch):
    lines = [_line("JE-1", "300", "0", "400")]
    monkeypatch.setattr(registry, "get_account_ledger", lambda **kwargs: _ledger(lines))
    db = _db_returning(_account(7, "1110", "Main Bank"))

    result = registry.tool_get_account_ledger(db=db, company_id=1, account_identifier="1110")

    assert result["account_code"] == "1110"
    # One query: the code matched, so the name search never ran.
    assert db.scalars.call_count == 1


def test_get_account_ledger_reports_the_currency_the_report_is_in(monkeypatch):
    """[CUR-2] resolves a report to one currency; that is the unit of these
    figures, and it is not necessarily the account's own."""
    monkeypatch.setattr(
        registry, "get_account_ledger",
        lambda **kwargs: _ledger([_line("JE-1", "300", "0", "400")], currency="YER"),
    )

    result = registry.tool_get_account_ledger(
        db=_db_returning(_account(currency="USD")), company_id=1, account_identifier="1110"
    )

    assert result["currency"] == "YER"
