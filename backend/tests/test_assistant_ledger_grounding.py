# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConversationTurn,
    PageContext,
)
from app.modules.accounting.services import gemini_assistant_service as service


def _account(account_id=11, code="1100", name="Cash"):
    return SimpleNamespace(id=account_id, code=code, name=name, account_type="asset")


def _ledger():
    line = SimpleNamespace(journal_entry_id=91, entry_no="JE-91", entry_date=date(2026, 7, 10), description="Receipt", debit=Decimal("500.00"), credit=Decimal("0.00"), running_balance=Decimal("2500.00"))
    return SimpleNamespace(account_id=11, account_code="1100", account_name="Cash", account_type="asset", start_date=None, end_date=None, opening_balance=Decimal("2000.00"), closing_balance=Decimal("2500.00"), lines=[line])


def test_account_ledger_resolves_exact_code_and_serializes_decimal_values(monkeypatch):
    account = _account()
    monkeypatch.setattr(service, "list_accounts", lambda **_: [account])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="What is the balance of account 1100?", page_context=PageContext(), language="en")
    assert reply.grounding.kind == "account_ledger"
    assert reply.grounding.account["account_id"] == 11
    assert reply.grounding.metrics == {"opening_balance": "2000.00", "total_debit": "500.00", "total_credit": "0.00", "closing_balance": "2500.00"}
    assert reply.grounding.entries[0]["running_balance"] == "2500.00"
    assert "1100" in reply.reply
    assert "Cash" in reply.reply
    assert "account_id" not in reply.reply
    assert "journal_entry_id" not in reply.reply
    assert "ID: 11" not in reply.reply
    assert "account ID 11" not in reply.reply


def test_account_ledger_resolves_exact_name_and_rejects_missing_accounts(monkeypatch):
    account = _account(name="Cash")
    monkeypatch.setattr(service, "list_accounts", lambda **_: [account])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    found = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="What is the cash account balance?", page_context=PageContext(), language="en")
    assert found.grounding.kind == "account_ledger"
    monkeypatch.setattr(service, "list_accounts", lambda **_: [])
    missing = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="What is the balance of account Missing?", page_context=PageContext(), language="en")
    assert missing.intent == "clarification"
    assert "could not find" in missing.reply


def test_account_ledger_does_not_choose_between_multiple_exact_matches(monkeypatch):
    monkeypatch.setattr(service, "list_accounts", lambda **_: [_account(11, "1100", "Cash"), _account(12, "1200", "Cash")])
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="What is the cash account balance?", page_context=PageContext(), language="en")
    assert reply.intent == "clarification"
    assert "more than one" in reply.reply


def test_general_ledger_is_bounded_and_read_only(monkeypatch):
    ledger = _ledger()
    accounts = [SimpleNamespace(account_id=i, account_code=f"{i:04d}", account_name=f"Account {i}", account_type="asset", opening_balance=Decimal("0.00"), closing_balance=Decimal("1.00"), lines=[]) for i in range(25)]
    monkeypatch.setattr(service, "get_general_ledger", lambda **_: SimpleNamespace(start_date=None, end_date=None, accounts=accounts))
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="Show the general ledger account summary", page_context=PageContext(), language="en")
    assert reply.grounding.kind == "general_ledger"
    assert len(reply.grounding.accounts) == 20
    assert reply.grounding.summary.total_accounts == 25
    assert reply.grounding.summary.has_more is True
    assert not reply.grounding.reference.filters.get("url")
    assert ledger is not None


def test_account_resolution_is_company_scoped(monkeypatch):
    calls = []
    def accounts(**kwargs):
        calls.append(kwargs["company_id"])
        return [_account()]
    monkeypatch.setattr(service, "list_accounts", accounts)
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    service.dispatch_gemini_assistant(db=None, company_id=99, user_role="viewer", message="What is the balance of account 1100?", page_context=PageContext(), language="en")
    assert calls == [99]


def test_account_ledger_routing_and_target_extraction_regressions():
    assert service._structured_report_kind("What is the balance of account 1100") == "account_ledger"
    assert service._extract_account_target("What is the balance of account 1100") == "1100"
    assert service._extract_account_target("What is the cash account balance") == "cash"
    assert service._extract_account_target("What is the bank account balance") == "bank"
    assert service._extract_account_target("Show the cash account ledger") == "cash"
    assert service._extract_account_target("Show the bank account ledger") == "bank"
    assert service._structured_report_kind("Show the general ledger account summary") == "general_ledger"


def test_orchestrator_hint_does_not_replace_exact_legacy_account_target(monkeypatch):
    account = _account(name="Cash")
    monkeypatch.setattr(service, "list_accounts", lambda **_: [account])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service._structured_report_reply(
        db=None,
        company_id=8,
        message="What is the cash account balance?",
        language="en",
        page_context=PageContext(),
        kind="account_ledger",
        account_target="cash account",
    )
    assert reply.grounding.kind == "account_ledger"


def test_structural_account_prefix_is_removed_without_corrupting_account_suffix():
    assert service._extract_account_target("What is the balance of account Main Bank?") == "main bank"
    assert service._extract_account_target("What is the Cash Account account balance?") == "cash account"
    assert service._extract_account_target("What is the closing balance of Sales") == "sales"
    assert service._extract_account_target("How much was debited to Rent Expense") == "rent expense"
    assert service._extract_account_target("Show transactions for Rent Expense") == "rent expense"
    assert service._extract_account_target("\u0645\u0627 \u0631\u0635\u064a\u062f \u062d\u0633\u0627\u0628 \u0627\u0644\u0646\u0642\u062f\u064a\u0629\u061f") == "\u0627\u0644\u0646\u0642\u062f\u064a\u0629"
    assert service._extract_account_target("\u0627\u0639\u0631\u0636 \u062f\u0641\u062a\u0631 \u0623\u0633\u062a\u0627\u0630 \u062d\u0633\u0627\u0628 \u0627\u0644\u0628\u0646\u0643") == "\u0627\u0644\u0628\u0646\u0643"
    assert service._extract_account_target("\u0643\u0645 \u062f\u0627\u0626\u0646 \u062d\u0633\u0627\u0628 \u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a\u061f") == "\u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a"
    assert service._extract_account_target("\u0645\u0627 \u0631\u0635\u064a\u062f \u062d\u0633\u0627\u0628 1100\u061f") == "1100"
    assert service._structured_report_kind("What is net profit") is None
    assert service._structured_report_kind("Is the balance sheet balanced") == "balance_sheet"


def test_bare_balance_does_not_guess_an_account():
    assert service._structured_report_kind("balance") is None
    assert service._extract_account_target("balance") is None


@pytest.mark.parametrize("message", ["إيش الموجود بحساب البنك؟", "ما رصيد حساب البنك؟"])
def test_arabic_bank_alias_resolves_unique_main_bank_in_arabic(monkeypatch, message):
    monkeypatch.setattr(
        service,
        "list_accounts",
        lambda **_: [_account(11, "1110", "Main Bank"), _account(12, "5100", "Rent Expense")],
    )
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message=message,
        page_context=PageContext(),
        language="en",
    )
    assert reply.grounding.kind == "account_ledger"
    assert reply.grounding.account["account_name"] == "Main Bank"
    assert "دفتر أستاذ الحساب" in reply.reply


def test_english_bank_alias_resolves_unique_main_bank_in_english(monkeypatch):
    monkeypatch.setattr(service, "list_accounts", lambda **_: [_account(11, "1110", "Main Bank")])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="Show the bank balance", page_context=PageContext(), language="ar")
    assert reply.grounding.account["account_name"] == "Main Bank"
    assert reply.reply.startswith("Account ledger")


def test_bank_alias_is_ambiguous_and_does_not_match_bank_charges(monkeypatch):
    monkeypatch.setattr(
        service,
        "list_accounts",
        lambda **_: [
            _account(11, "1110", "Main Bank"),
            _account(12, "1120", "Savings Bank"),
            _account(13, "5130", "Bank Charges"),
        ],
    )
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="إيش الموجود بحساب البنك؟", page_context=PageContext(), language="ar")
    assert reply.intent == "clarification"
    assert "أكثر من حساب" in reply.reply
    assert "Main Bank" in reply.reply
    assert "Savings Bank" in reply.reply
    assert "Bank Charges" not in reply.reply


def test_cash_alias_resolves_petty_cash_not_cash_expense(monkeypatch):
    monkeypatch.setattr(
        service,
        "list_accounts",
        lambda **_: [_account(11, "1130", "Petty Cash"), _account(12, "5140", "Cash Expense")],
    )
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="كم عندنا في الصندوق؟", page_context=PageContext(), language="ar")
    assert reply.grounding.account["account_name"] == "Petty Cash"


def test_alias_resolution_supports_full_arabic_hint_and_remains_company_scoped(monkeypatch):
    calls = []
    def scoped_accounts(**kwargs):
        calls.append(kwargs["company_id"])
        return [_account(11, "1110", "Main Bank")]
    monkeypatch.setattr(service, "list_accounts", scoped_accounts)
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    reply = service.dispatch_gemini_assistant(db=None, company_id=77, user_role="viewer", message="ما رصيد حساب البنك؟", page_context=PageContext(), language="ar")
    assert reply.grounding.account["account_name"] == "Main Bank"
    assert calls == [77]


def test_exact_account_code_stays_above_alias_matching():
    accounts = [_account(11, "1110", "Main Bank"), _account(12, "1120", "Savings Bank")]
    candidates = service._resolve_account_candidates(accounts, "1110")
    assert [candidate.id for candidate in candidates] == [11]


def test_arabic_alias_not_found_reply_uses_latest_message_language(monkeypatch):
    monkeypatch.setattr(service, "list_accounts", lambda **_: [_account(13, "5130", "Bank Charges")])
    reply = service.dispatch_gemini_assistant(db=None, company_id=8, user_role="viewer", message="إيش الموجود بحساب البنك؟", page_context=PageContext(), language="en")
    assert reply.intent == "clarification"
    assert reply.reply.startswith("لم أجد")


@pytest.mark.parametrize(
    "message",
    (
        "اعرض رصيد الحساب",
        "ما رصيد الحساب؟",
        "كم رصيد الحساب؟",
        "أريد رصيد الحساب",
        "اعرض كشف الحساب",
        "اعرض حركة الحساب",
        "ما الرصيد الختامي للحساب؟",
        "كم مدين الحساب؟",
        "كم دائن الحساب؟",
    ),
)
def test_ambiguous_arabic_account_requests_ask_for_account_target(
    monkeypatch,
    message,
):
    def unexpected_call(*_, **__):
        raise AssertionError("ambiguous account request reached report routing")

    monkeypatch.setattr(service, "_classify_intent", unexpected_call)
    monkeypatch.setattr(service, "_tool_get_profit_loss", unexpected_call)
    monkeypatch.setattr(service, "get_balance_sheet", unexpected_call)
    monkeypatch.setattr(service, "get_trial_balance", unexpected_call)
    monkeypatch.setattr(service, "get_account_ledger", unexpected_call)
    monkeypatch.setattr(service, "get_general_ledger", unexpected_call)
    monkeypatch.setattr(service, "_call_gemini_for_answer", unexpected_call)
    monkeypatch.setattr(service, "parse_transaction_message", unexpected_call)

    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message=message,
        page_context=PageContext(
            route="/reports/account-ledger",
            page="account_ledger",
        ),
        language="en",
    )

    assert reply.intent == "clarification"
    assert reply.reply == (
        "ما الحساب الذي تريد عرض رصيده؟ اذكر اسم الحساب أو رمزه كما يظهر في دليل الحسابات."
    )
    assert reply.grounding is None
    assert reply.data_sources == []
    assert not any(character.isdigit() for character in reply.reply)
    assert all(
        total_name not in reply.reply
        for total_name in ("الإيرادات", "المصروفات", "صافي الربح", "إجمالي الأصول")
    )


@pytest.mark.parametrize(
    "message",
    (
        "Show the account balance",
        "What is the account balance",
        "Show the account ledger",
        "Show account activity",
        "What is the closing balance of the account",
        "How much was debited to the account",
        "How much was credited to the account",
    ),
)
def test_ambiguous_english_account_requests_ask_for_account_target(message):
    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message=message,
        page_context=PageContext(),
        language="ar",
    )

    assert reply.intent == "clarification"
    assert reply.reply == (
        "Which account balance would you like to see? Provide the account name "
        "or code as shown in the chart of accounts."
    )
    assert reply.grounding is None
    assert reply.data_sources == []


@pytest.mark.parametrize(
    "message, account_name",
    (
        ("ما رصيد حساب النقدية؟", "النقدية"),
        ("اعرض رصيد حساب البنك", "البنك"),
        ("اعرض حركة حساب المصروفات", "المصروفات"),
    ),
)
def test_explicit_arabic_account_targets_still_use_account_ledger(
    monkeypatch,
    message,
    account_name,
):
    monkeypatch.setattr(
        service,
        "list_accounts",
        lambda **_: [_account(name=account_name)],
    )
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())

    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message=message,
        page_context=PageContext(),
        language="ar",
    )

    assert reply.intent == "answer_account_ledger_question"
    assert reply.grounding.kind == "account_ledger"
    assert reply.grounding.account["account_name"] == account_name


def test_transactions_for_named_account_still_use_account_ledger(monkeypatch):
    monkeypatch.setattr(
        service,
        "list_accounts",
        lambda **_: [_account(name="Rent Expense")],
    )
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())

    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="Show transactions for Rent Expense.",
        page_context=PageContext(),
        language="en",
    )

    assert reply.intent == "answer_account_ledger_question"
    assert reply.grounding.kind == "account_ledger"
    assert reply.grounding.requested_metric == "transactions"


def test_valid_same_conversation_ledger_grounding_supports_balance_followup(
    monkeypatch,
):
    monkeypatch.setattr(service, "list_accounts", lambda **_: [_account()])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    original = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="What is the balance of account 1100?",
        page_context=PageContext(),
        language="en",
    )

    def unexpected_call(*_, **__):
        raise AssertionError("validated grounding follow-up fetched another report")

    monkeypatch.setattr(service, "list_accounts", unexpected_call)
    monkeypatch.setattr(service, "get_account_ledger", unexpected_call)
    followup = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="اعرض الرصيد",
        page_context=PageContext(),
        language="en",
        prior_grounding=original.grounding.model_dump(mode="json"),
    )

    assert followup.intent == "answer_account_ledger_question"
    assert followup.grounding.kind == "account_ledger"
    assert "1100" in followup.reply
    assert "2500.00" in followup.reply


def test_this_account_transactions_require_same_conversation_grounding(monkeypatch):
    without_context = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="Show this accounts transactions",
        page_context=PageContext(),
        language="en",
    )
    assert without_context.intent == "clarification"
    assert without_context.grounding is None

    monkeypatch.setattr(service, "list_accounts", lambda **_: [_account()])
    monkeypatch.setattr(service, "get_account_ledger", lambda **_: _ledger())
    original = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="What is the balance of account 1100?",
        page_context=PageContext(),
        language="en",
    )

    with_context = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="Show this accounts transactions",
        page_context=PageContext(),
        language="en",
        prior_grounding=original.grounding.model_dump(mode="json"),
    )
    assert with_context.intent == "answer_account_ledger_question"
    assert with_context.grounding.kind == "account_ledger"
    assert "JE-91" in with_context.reply


@pytest.mark.parametrize(
    "prior_grounding",
    (
        None,
        {"status": "unavailable", "kind": "account_ledger"},
        {
            "status": "grounded",
            "kind": "account_ledger",
            "account": "malformed",
        },
    ),
)
def test_new_or_invalid_conversation_context_cannot_supply_an_account(
    prior_grounding,
):
    reply = service.dispatch_gemini_assistant(
        db=None,
        company_id=8,
        user_role="viewer",
        message="اعرض الرصيد",
        page_context=PageContext(),
        language="ar",
        history=[
            ConversationTurn(
                role="assistant",
                content="Earlier unrelated text mentioned account 1100 Cash.",
            )
        ],
        prior_grounding=prior_grounding,
    )

    assert reply.intent == "clarification"
    assert reply.grounding is None
    assert "اذكر اسم الحساب أو رمزه" in reply.reply
