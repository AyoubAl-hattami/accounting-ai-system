# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import gemini_assistant_service as service


def _report():
    line = lambda i, c, n, amount: SimpleNamespace(account_id=i, account_code=c, account_name=n, amount=Decimal(amount))
    return SimpleNamespace(
        as_of_date=date(2026, 7, 14),
        total_assets=Decimal("25000.00"), total_liabilities=Decimal("8000.00"),
        equity_accounts_total=Decimal("12000.00"), prior_year_earnings=Decimal("1000.00"),
        retained_earnings=Decimal("1000.00"), current_year_earnings=Decimal("4000.00"),
        total_equity=Decimal("17000.00"), total_liabilities_and_equity=Decimal("25000.00"),
        asset_lines=[line(1, "1100", "Cash", "25000.00")],
        liability_lines=[line(2, "2100", "Payables", "8000.00")],
        equity_lines=[line(3, "3100", "Capital", "12000.00")],
    )


def test_arabic_assets_question_returns_exact_balance_sheet_grounding(monkeypatch):
    monkeypatch.setattr(service, "get_balance_sheet", lambda **_: _report())
    reply = service.dispatch_gemini_assistant(
        db=None, company_id=7, user_role="viewer", message="كم إجمالي الأصول؟",
        page_context=PageContext(), language="ar",
    )
    assert reply.grounding.kind == "balance_sheet"
    assert reply.grounding.metrics["total_assets"] == "25000.00"
    assert reply.grounding.metrics["difference"] == "0.00"
    assert reply.grounding.metrics["is_balanced"] is True


def test_english_equity_question_uses_exact_decimal_equation(monkeypatch):
    monkeypatch.setattr(service, "get_balance_sheet", lambda **_: _report())
    reply = service.dispatch_gemini_assistant(
        db=None, company_id=7, user_role="viewer", message="What is total equity?",
        page_context=PageContext(), language="en",
    )
    assert reply.grounding.kind == "balance_sheet"
    assert reply.grounding.requested_metric == "equity"
    assert Decimal(reply.grounding.metrics["total_assets"]) - Decimal(reply.grounding.metrics["liabilities_and_equity"]) == Decimal(reply.grounding.metrics["difference"])


def test_balance_sheet_reference_is_allowlisted_and_has_no_company_id():
    from app.modules.accounting.schemas.gemini_assistant_schemas import BalanceSheetGrounding
    grounding = BalanceSheetGrounding(status="grounded", kind="balance_sheet", reference={"type": "report", "report": "balance_sheet", "filters": {"as_of_date": "2026-07-14"}})
    assert grounding.reference.report == "balance_sheet"
    assert "company_id" not in grounding.model_dump()
    assert "url" not in grounding.model_dump()


def test_unavailable_balance_sheet_has_no_financial_values(monkeypatch):
    def fail(**_):
        raise RuntimeError("private database error")
    monkeypatch.setattr(service, "get_balance_sheet", fail)
    reply = service.dispatch_gemini_assistant(db=None, company_id=7, user_role="viewer", message="Show the balance sheet", page_context=PageContext(), language="en")
    assert reply.grounding.status == "unavailable"
    assert "private database error" not in reply.reply
    assert "25000" not in reply.reply


def test_persisted_balance_sheet_accounts_followup_uses_same_grounding():
    grounding = {
        "status": "grounded", "kind": "balance_sheet", "requested_metric": "assets",
        "period": {"as_of_date": "2026-07-14", "label": "As of 2026-07-14"},
        "metrics": {"total_assets": "25000.00"},
        "sections": [{"section": "assets", "accounts": [{"account_code": "1100", "account_name": "Cash", "balance": "2200.00"}]}],
        "reference": {"type": "report", "report": "balance_sheet", "filters": {"as_of_date": "2026-07-14"}},
    }
    reply = service._structured_followup_reply(grounding, ("accounts", "show the accounts"), "en")
    assert reply.grounding.kind == "balance_sheet"
    assert "2026-07-14" in reply.reply
    assert "1100" in reply.reply
    assert "2200.00" in reply.reply

def test_structured_accounts_without_grounding_requires_clarification():
    assert service._structured_followup_reply(None, ("accounts", "show the accounts"), "en") is None
