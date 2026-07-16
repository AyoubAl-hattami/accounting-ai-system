# -*- coding: utf-8 -*-
from decimal import Decimal
from types import SimpleNamespace

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import gemini_assistant_service as service


def _trial(debit="42500.00", credit="42500.00"):
    line = SimpleNamespace(account_id=1, account_code="1100", account_name="Cash", account_type="asset", debit_balance=Decimal("100.00"), credit_balance=Decimal("0.00"))
    return SimpleNamespace(as_of_date=None, total_debit=Decimal(debit), total_credit=Decimal(credit), lines=[line], is_balanced=Decimal(debit) == Decimal(credit))


def test_arabic_total_debit_returns_trial_balance_grounding(monkeypatch):
    monkeypatch.setattr(service, "get_trial_balance", lambda **_: _trial())
    reply = service.dispatch_gemini_assistant(db=None, company_id=4, user_role="viewer", message="كم إجمالي المدين في ميزان المراجعة؟", page_context=PageContext(), language="ar")
    assert reply.grounding.kind == "trial_balance"
    assert reply.grounding.metrics["total_debit"] == "42500.00"
    assert reply.grounding.metrics["total_credit"] == "42500.00"
    assert reply.grounding.metrics["difference"] == "0.00"
    assert reply.grounding.metrics["is_balanced"] is True


def test_english_credit_question_preserves_nonzero_decimal_difference(monkeypatch):
    monkeypatch.setattr(service, "get_trial_balance", lambda **_: _trial("42500.01", "42500.00"))
    reply = service.dispatch_gemini_assistant(db=None, company_id=4, user_role="viewer", message="What is the total credit in the trial balance?", page_context=PageContext(), language="en")
    assert reply.grounding.kind == "trial_balance"
    assert reply.grounding.metrics["total_credit"] == "42500.00"
    assert reply.grounding.metrics["difference"] == "0.01"
    assert reply.grounding.metrics["is_balanced"] is False


def test_trial_balance_accounts_are_bounded_and_ordered(monkeypatch):
    lines = [SimpleNamespace(account_id=i, account_code=f"{i:04d}", account_name=f"Account {i}", account_type="asset", debit_balance=Decimal("1.00"), credit_balance=Decimal("0.00")) for i in range(60)]
    monkeypatch.setattr(service, "get_trial_balance", lambda **_: SimpleNamespace(as_of_date=None, total_debit=Decimal("60.00"), total_credit=Decimal("0.00"), lines=lines, is_balanced=False))
    reply = service.dispatch_gemini_assistant(db=None, company_id=4, user_role="viewer", message="Show the trial balance accounts", page_context=PageContext(), language="en")
    assert len(reply.grounding.accounts) == 50
    assert reply.grounding.summary.total_accounts == 60
    assert reply.grounding.summary.has_more is True
    assert [row["account_code"] for row in reply.grounding.accounts[:2]] == ["0000", "0001"]


def test_empty_generic_accounts_request_does_not_use_unrelated_grounding():
    assert service._structured_report_kind("اعرض الحسابات") is None


def test_show_accounts_uses_same_conversation_trial_balance_grounding(monkeypatch):
    monkeypatch.setattr(service, "get_trial_balance", lambda **_: _trial())
    original = service.dispatch_gemini_assistant(
        db=None,
        company_id=4,
        user_role="viewer",
        message="Show the trial balance",
        page_context=PageContext(),
        language="en",
    )
    follow_up = service.dispatch_gemini_assistant(
        db=None,
        company_id=4,
        user_role="viewer",
        message="Show the accounts",
        page_context=PageContext(),
        language="en",
        prior_grounding=original.grounding.model_dump(mode="json"),
    )
    assert follow_up.grounding.kind == "trial_balance"
    assert follow_up.grounding.accounts[0]["account_name"] == "Cash"


def test_show_accounts_without_report_grounding_requests_clarification():
    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=4,
        user_role="viewer",
        message="Show the accounts",
        page_context=PageContext(),
        language="en",
    )
    assert reply.intent == "clarification"
    assert reply.grounding is None


def _balanced_question_reply(monkeypatch, *, message, debit, credit, language):
    monkeypatch.setattr(
        service,
        "get_trial_balance",
        lambda **_: _trial(debit, credit),
    )
    return service.dispatch_gemini_assistant(
        db=None,
        company_id=4,
        user_role="viewer",
        message=message,
        page_context=PageContext(),
        language=language,
    )


def test_arabic_balanced_question_states_explicit_decimal_safe_conclusion(monkeypatch):
    reply = _balanced_question_reply(
        monkeypatch,
        message="هل ميزان المراجعة متوازن؟",
        debit="6200.00",
        credit="6200.00",
        language="en",
    )
    assert reply.reply.startswith("ميزان المراجعة متوازن وفقا لبيانات النظام.")
    assert "إجمالي المدين: 6200.00" in reply.reply
    assert "إجمالي الدائن: 6200.00" in reply.reply
    assert "الفرق: 0.00" in reply.reply
    assert reply.grounding.kind == "trial_balance"
    assert reply.grounding.metrics["is_balanced"] is True


def test_english_balanced_question_states_explicit_conclusion(monkeypatch):
    reply = _balanced_question_reply(
        monkeypatch,
        message="Is the trial balance balanced?",
        debit="6200.00",
        credit="6200.00",
        language="ar",
    )
    assert reply.reply.startswith("The trial balance is balanced according to the system data.")
    assert "Total debit: 6200.00" in reply.reply
    assert "Total credit: 6200.00" in reply.reply
    assert "Difference: 0.00" in reply.reply
    assert reply.grounding.kind == "trial_balance"


def test_arabic_unbalanced_question_states_exact_difference(monkeypatch):
    reply = _balanced_question_reply(
        monkeypatch,
        message="هل ميزان المراجعة متوازن؟",
        debit="6200.01",
        credit="6200.00",
        language="en",
    )
    assert reply.reply.startswith("ميزان المراجعة غير متوازن وفقا لبيانات النظام.")
    assert "الفرق: 0.01" in reply.reply
    assert reply.grounding.metrics["difference"] == "0.01"
    assert reply.grounding.metrics["is_balanced"] is False


def test_english_unbalanced_question_states_exact_difference(monkeypatch):
    reply = _balanced_question_reply(
        monkeypatch,
        message="Is the trial balance balanced?",
        debit="6200.01",
        credit="6200.00",
        language="ar",
    )
    assert reply.reply.startswith("The trial balance is not balanced according to the system data.")
    assert "Difference: 0.01" in reply.reply
    assert reply.grounding.kind == "trial_balance"
