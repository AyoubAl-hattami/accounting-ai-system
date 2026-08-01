"""
Tests for semantic transaction parsing and account mapping.

Unit tests use mocked Gemini output.
Integration tests hit the live server and are tolerant of Gemini variance.
"""

import json
import sys
from types import SimpleNamespace

import requests
import re
from unittest.mock import patch, MagicMock

# Used only in unit tests (mocked DB calls, not real DB rows)
_MOCK_CID = 1

# ── Sample accounts (synthetic, not from seed DB) ─────────────────────────────

SAMPLE_ACCOUNTS = [
    {"id": 1, "code": "1000", "name": "Assets", "account_type": "asset", "is_active": True},
    {"id": 2, "code": "1110", "name": "Main Bank", "account_type": "asset", "is_active": True},
    {"id": 3, "code": "1200", "name": "Accounts Receivable", "account_type": "asset", "is_active": True},
    {"id": 4, "code": "2000", "name": "Liabilities", "account_type": "liability", "is_active": True},
    {"id": 5, "code": "2100", "name": "Accounts Payable", "account_type": "liability", "is_active": True},
    {"id": 6, "code": "3000", "name": "Equity", "account_type": "equity", "is_active": True},
    {"id": 7, "code": "3100", "name": "Owner Capital", "account_type": "equity", "is_active": True},
    {"id": 8, "code": "4000", "name": "Income", "account_type": "income", "is_active": True},
    {"id": 9, "code": "4100", "name": "Sales Revenue", "account_type": "income", "is_active": True},
    {"id": 10, "code": "5000", "name": "Expenses", "account_type": "expense", "is_active": True},
    {"id": 11, "code": "5100", "name": "Rent Expense", "account_type": "expense", "is_active": True},
    {"id": 12, "code": "5200", "name": "Software Expense", "account_type": "expense", "is_active": True},
    {"id": 13, "code": "1120", "name": "Cash", "account_type": "asset", "is_active": True},
    {"id": 14, "code": "5300", "name": "Utilities Expense", "account_type": "expense", "is_active": True},
]


def _fake_gemini_modules(response_payload: dict):
    """Build fake google/genai modules for parser tests."""
    response = SimpleNamespace(text=json.dumps(response_payload))
    client = MagicMock()
    client.models.generate_content.return_value = response
    fake_genai = SimpleNamespace(Client=MagicMock(return_value=client))
    fake_google = SimpleNamespace(genai=fake_genai)
    return fake_google, fake_genai, client


def _gemini_request(base_url, headers, company_id, message, language="ar"):
    return requests.post(
        f"{base_url}/ai/gemini-assistant",
        headers=headers,
        json={
            "company_id": company_id,
            "message": message,
            "language": language,
            "page_context": {"route": "/dashboard", "page": "dashboard", "filters": {}},
            "history": [],
        },
    )


# ── Unit tests: account mapper ────────────────────────────────────────────────

class TestAccountMapper:
    """Unit tests for the account mapper (no live API needed)."""

    def test_expense_payment_maps_correctly(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=300,
            description="دفع مصروف كهرباء",
            debit_account_hint="utilities expense",
            credit_account_hint="bank",
            income_or_expense_nature="electricity",
            payment_source_hint="bank",
            confidence=0.9,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.debit_account_id is not None
        debit = next(a for a in SAMPLE_ACCOUNTS if a["id"] == mapped.debit_account_id)
        assert debit["account_type"] == "expense"
        assert mapped.credit_account_id is not None
        credit = next(a for a in SAMPLE_ACCOUNTS if a["id"] == mapped.credit_account_id)
        assert credit["account_type"] == "asset"
        assert mapped.needs_clarification is False

    def test_expense_missing_source_asks_clarification(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=300,
            description="دفع مصروف كهرباء",
            debit_account_hint="utilities expense",
            payment_source_hint="unknown",
            confidence=0.85,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.needs_clarification is True
        assert mapped.clarification_question is not None
        assert "البنك" in mapped.clarification_question or "bank" in mapped.clarification_question.lower()

    def test_income_receipt_maps_correctly(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="income_receipt",
            amount=1000,
            description="استلام مبلغ",
            debit_account_hint="bank",
            credit_account_hint="sales revenue",
            receiving_account_hint="bank",
            confidence=0.8,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.debit_account_id is not None
        debit = next(a for a in SAMPLE_ACCOUNTS if a["id"] == mapped.debit_account_id)
        assert debit["account_type"] == "asset"
        assert "bank" in debit["name"].lower()
        assert mapped.credit_account_id is not None
        credit = next(a for a in SAMPLE_ACCOUNTS if a["id"] == mapped.credit_account_id)
        assert credit["account_type"] == "income"

    def test_bank_cash_transfer(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="bank_cash_transfer",
            amount=500,
            description="تحويل من البنك للصندوق",
            payment_source_hint="bank",
            receiving_account_hint="cash",
            confidence=0.9,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.debit_account_id is not None
        assert mapped.credit_account_id is not None
        assert mapped.debit_account_id != mapped.credit_account_id

    def test_supplier_payment_asks_source(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="supplier_payment",
            amount=1200,
            description="سداد مورد",
            debit_account_hint="accounts payable",
            payment_source_hint="unknown",
            confidence=0.7,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.needs_clarification is True
        assert len(mapped.clarification_options) >= 2

    def test_alias_electricity_matches_utilities(self):
        from app.modules.accounting.services.account_mapper import _find_alias_category
        assert _find_alias_category("كهرباء") == "utilities"
        assert _find_alias_category("كهربا") == "utilities"

    def test_alias_rent_matches(self):
        from app.modules.accounting.services.account_mapper import _find_alias_category
        assert _find_alias_category("إيجار") == "rent"

    def test_missing_specific_expense_uses_generic_expense_not_unrelated_account(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        accounts_without_utilities = [a for a in SAMPLE_ACCOUNTS if a["name"] != "Utilities Expense"]
        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=300,
            description="دفعت 300 كهربا من البنك",
            debit_account_hint="utilities expense",
            income_or_expense_nature="utilities",
            payment_source_hint="bank",
            confidence=0.8,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, accounts_without_utilities, "ar")
        assert mapped.debit_account_name == "Expenses"
        assert mapped.debit_account_name != "Rent Expense"
        assert mapped.credit_account_name == "Main Bank"

    def test_explicit_cash_does_not_fall_back_to_bank_when_cash_missing(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
        from app.modules.accounting.services.account_mapper import map_to_accounts

        accounts_without_cash = [a for a in SAMPLE_ACCOUNTS if a["name"] != "Cash"]
        parsed = ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=300,
            description="دفعت 300 كهربا من الصندوق",
            debit_account_hint="utilities expense",
            income_or_expense_nature="utilities",
            payment_source_hint="cash",
            confidence=0.8,
            needs_clarification=False,
        )
        mapped = map_to_accounts(parsed, accounts_without_cash, "ar")
        assert mapped.debit_account_name == "Utilities Expense"
        assert mapped.credit_account_id is None
        assert mapped.credit_account_name is None


class TestSemanticParserFallback:
    """Unit tests for deterministic parsing when Gemini is unavailable."""

    def test_electricity_payment_without_source_parses_to_mapper_clarification(self):
        from app.modules.accounting.services import gemini_transaction_parser as parser
        from app.modules.accounting.services.account_mapper import map_to_accounts

        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"

        with patch.object(parser, "settings", mock_settings):
            parsed = parser.parse_transaction_message("دفعت 300 كهربا", SAMPLE_ACCOUNTS, "ar")

        assert parsed is not None
        assert parsed.intent == "create_journal_entry"
        assert parsed.transaction_type == "expense_payment"
        assert parsed.amount == 300
        assert parsed.debit_account_hint == "utilities expense"
        assert parsed.payment_source_hint == "unknown"

        mapped = map_to_accounts(parsed, SAMPLE_ACCOUNTS, "ar")
        assert mapped.needs_clarification is True
        assert mapped.clarification_question is not None
        assert "البنك" in mapped.clarification_question
        assert "الصندوق" in mapped.clarification_question

    def test_clear_accounting_message_uses_local_parser_before_gemini(self):
        from app.modules.accounting.services import gemini_transaction_parser as parser

        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = "configured"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        fake_google, fake_genai, client = _fake_gemini_modules({"intent": "not_accounting"})
        client.models.generate_content.side_effect = AssertionError("Gemini should not be called")

        with patch.object(parser, "settings", mock_settings), patch.dict(
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            parsed = parser.parse_transaction_message("دفعت 300 كهربا", SAMPLE_ACCOUNTS, "ar")

        assert parsed is not None
        assert parsed.intent == "create_journal_entry"
        assert parsed.transaction_type == "expense_payment"
        assert parsed.amount == 300
        assert parsed.payment_source_hint == "unknown"
        client.models.generate_content.assert_not_called()

    def test_bad_gemini_not_accounting_falls_back_to_local_parser(self):
        from app.modules.accounting.services import gemini_transaction_parser as parser

        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = "configured"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        fake_google, fake_genai, client = _fake_gemini_modules({"intent": "not_accounting", "confidence": 0.2})

        with patch.object(parser, "settings", mock_settings), patch.object(
            parser, "_LOCAL_FIRST_MIN_CONFIDENCE", 0.95
        ), patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}):
            parsed = parser.parse_transaction_message("دفعت 300 كهربا", SAMPLE_ACCOUNTS, "ar")

        assert parsed is not None
        assert parsed.intent == "create_journal_entry"
        assert parsed.transaction_type == "expense_payment"
        assert parsed.amount == 300
        assert parsed.debit_account_hint == "utilities expense"
        client.models.generate_content.assert_called_once()

    def test_generic_gemini_clarification_falls_back_to_local_parser(self):
        from app.modules.accounting.services import gemini_transaction_parser as parser

        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = "configured"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        fake_google, fake_genai, client = _fake_gemini_modules({
            "intent": "clarification",
            "transaction_type": "unknown",
            "amount": None,
            "confidence": 0.2,
            "needs_clarification": True,
            "clarification_question": "لم أفهم. كيف يمكنني مساعدتك؟",
            "clarification_options": [],
        })

        with patch.object(parser, "settings", mock_settings), patch.object(
            parser, "_LOCAL_FIRST_MIN_CONFIDENCE", 0.95
        ), patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}):
            parsed = parser.parse_transaction_message("دفعت 300 كهربا", SAMPLE_ACCOUNTS, "ar")

        assert parsed is not None
        assert parsed.intent == "create_journal_entry"
        assert parsed.transaction_type == "expense_payment"
        assert parsed.amount == 300
        client.models.generate_content.assert_called_once()


class TestAssistantServiceSemanticFallback:
    """Dispatcher-level tests for weak Gemini parser output."""

    def test_dispatcher_rescues_bad_gemini_output_while_available(self):
        from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
        from app.modules.accounting.services import gemini_assistant_service as service
        from app.modules.accounting.services import gemini_transaction_parser as parser

        mock_settings = MagicMock()
        mock_settings.GEMINI_API_KEY = "configured"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        fake_google, fake_genai, client = _fake_gemini_modules({"intent": "not_accounting", "confidence": 0.2})

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS), patch.object(
            parser, "settings", mock_settings
        ), patch.object(parser, "_LOCAL_FIRST_MIN_CONFIDENCE", 0.95), patch.dict(
            sys.modules, {"google": fake_google, "google.genai": fake_genai}
        ):
            reply = service.dispatch_gemini_assistant(
                db=MagicMock(),
                company_id=_MOCK_CID,
                user_role="admin",
                message="دفعت 300 كهربا",
                page_context=PageContext(route="/dashboard", page="dashboard", filters={}),
                language="ar",
            )

        assert reply.intent == "clarification"
        assert reply.suggested_action is None
        assert "يمكنني مساعدتك في" not in reply.reply
        assert "البنك" in reply.reply
        assert "الصندوق" in reply.reply
        client.models.generate_content.assert_called_once()


class TestAssistantPendingClarification:
    """Multi-turn pending transaction clarification tests."""

    def _dispatch(self, service, message, *, pending=None, token=None, company_id=_MOCK_CID):
        from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext

        return service.dispatch_gemini_assistant(
            db=MagicMock(),
            company_id=company_id,
            user_role="admin",
            message=message,
            page_context=PageContext(route="/dashboard", page="dashboard", filters={}),
            language="ar",
            pending_transaction=pending,
            pending_context_token=token,
        )

    def test_first_message_returns_pending_payment_source(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            reply = self._dispatch(service, "دفعت 300 كهربا")

        assert reply.intent == "clarification"
        assert reply.suggested_action is None
        assert reply.pending_transaction is not None
        assert reply.pending_context_token
        assert reply.pending_transaction.amount == 300
        assert reply.pending_transaction.transaction_type == "expense_payment"
        assert reply.pending_transaction.debit_account_hint == "utilities expense"
        assert reply.pending_transaction.missing_fields == ["payment_source"]
        assert [option.value for option in reply.clarification_options] == ["bank", "cash"]

    def test_followup_cash_creates_preview_without_generic_help(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            first = self._dispatch(service, "دفعت 300 كهربا")
            second = self._dispatch(service, "الصندوق", pending=first.pending_transaction, token=first.pending_context_token)

        assert second.intent == "create_journal_draft"
        assert second.suggested_action is not None
        assert second.pending_transaction is None
        assert "يمكنني مساعدتك في" not in second.reply
        lines = second.suggested_action.payload.lines
        debit = next(line for line in lines if float(line.debit) == 300.0)
        credit = next(line for line in lines if float(line.credit) == 300.0)
        assert debit.account_name == "Utilities Expense"
        assert credit.account_name == "Cash"

    def test_followup_bank_creates_bank_preview(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            first = self._dispatch(service, "دفعت 300 كهربا")
            second = self._dispatch(service, "البنك", pending=first.pending_transaction, token=first.pending_context_token)

        assert second.intent == "create_journal_draft"
        lines = second.suggested_action.payload.lines
        assert any(line.account_name == "Utilities Expense" and float(line.debit) == 300.0 for line in lines)
        assert any(line.account_name == "Main Bank" and float(line.credit) == 300.0 for line in lines)

    def test_numeric_and_dialect_cash_answers_resolve_to_cash(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        for answer in ("2", "كاش"):
            with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
                first = self._dispatch(service, "دفعت 300 كهربا")
                second = self._dispatch(service, answer, pending=first.pending_transaction, token=first.pending_context_token)

            assert second.intent == "create_journal_draft"
            lines = second.suggested_action.payload.lines
            assert any(line.account_name == "Cash" and float(line.credit) == 300.0 for line in lines)

    def test_supplier_followup_continues_pending_transaction(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            first = self._dispatch(service, "دفعت للمورد 1200")
            second = self._dispatch(service, "سداد مورد", pending=first.pending_transaction, token=first.pending_context_token)

        assert first.pending_transaction is not None
        assert first.pending_transaction.transaction_type == "supplier_payment"
        assert first.pending_transaction.missing_fields == ["payment_source"]
        assert second.intent == "clarification"
        assert second.suggested_action is None
        assert second.pending_transaction is not None
        assert second.pending_transaction.transaction_type == "supplier_payment"
        assert "يمكنني مساعدتك في" not in second.reply
        assert "البنك" in second.reply and "الصندوق" in second.reply

    def test_standalone_clarification_answer_does_not_invent_transaction(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            reply = self._dispatch(service, "الصندوق")

        assert reply.intent == "clarification"
        assert reply.suggested_action is None
        assert reply.pending_transaction is None
        assert "ما العملية" in reply.reply
        assert "يمكنني مساعدتك في" not in reply.reply

    def test_pending_context_cannot_cross_company(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            first = self._dispatch(service, "دفعت 300 كهربا", company_id=_MOCK_CID)
            second = self._dispatch(service, "الصندوق", pending=first.pending_transaction, token=first.pending_context_token, company_id=_MOCK_CID + 1)

        assert second.intent == "clarification"
        assert second.suggested_action is None
        assert "الشركة الحالية" in second.reply

    def test_pending_preview_does_not_write_before_confirm(self):
        from app.modules.accounting.services import gemini_assistant_service as service

        db = MagicMock()
        with patch.object(service, "_tool_get_accounts", return_value=SAMPLE_ACCOUNTS):
            first = service.dispatch_gemini_assistant(
                db=db, company_id=_MOCK_CID, user_role="admin", message="دفعت 300 كهربا",
                page_context=__import__("app.modules.accounting.schemas.gemini_assistant_schemas", fromlist=["PageContext"]).PageContext(route="/dashboard", page="dashboard", filters={}),
                language="ar",
            )
            second = service.dispatch_gemini_assistant(
                db=db, company_id=_MOCK_CID, user_role="admin", message="الصندوق",
                page_context=__import__("app.modules.accounting.schemas.gemini_assistant_schemas", fromlist=["PageContext"]).PageContext(route="/dashboard", page="dashboard", filters={}),
                language="ar",
                pending_transaction=first.pending_transaction,
                pending_context_token=first.pending_context_token,
            )

        assert second.intent == "create_journal_draft"
        assert second.suggested_action is not None
        assert not db.add.called
        assert not db.commit.called


# ── Integration tests: semantic behavior ──────────────────────────────────────

class TestSemanticIntegration:
    """Integration tests against the live server.

    These tests verify that the assistant gives useful responses
    (either a draft preview or a specific clarification)
    instead of generic help menus.
    """

    def test_electricity_payment_no_source(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "دفعت 300 كهربا")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Expected draft/clarification, got {data['intent']}. Reply: {data['reply'][:200]}"
        if data["intent"] == "clarification":
            reply = data["reply"]
            assert any(w in reply for w in ["البنك", "الصندوق", "bank", "cash"]), \
                f"Clarification should ask about bank/cash. Reply: {reply[:300]}"

    def test_electricity_payment_with_bank(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "دفعت 300 كهرباء من البنك")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Got intent: {data['intent']}. Reply: {data['reply'][:200]}"
        if data["intent"] == "create_journal_draft":
            assert data["suggested_action"] is not None
            payload = data["suggested_action"]["payload"]
            assert payload["amount"] == 300.0 or any(
                float(l["debit"]) == 300.0 or float(l["credit"]) == 300.0
                for l in payload["lines"]
            )

    def test_dialect_electricity_phrase(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "خرجنا حق الكهرباء 300")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Expected draft/clarification, got {data['intent']}. Reply: {data['reply'][:200]}"

    def test_receipt_from_trader(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "استلمنا 1000 من تاجر الحليب")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Got intent: {data['intent']}. Reply: {data['reply'][:200]}"

    def test_supplier_payment_asks_clarification(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "دفعت للمورد 1200")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Got intent: {data['intent']}. Reply: {data['reply'][:200]}"

    def test_bank_to_cash_transfer(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "حولت 500 من البنك للصندوق")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("create_journal_draft", "clarification"), \
            f"Got intent: {data['intent']}. Reply: {data['reply'][:200]}"

    def test_preview_does_not_create_entry(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        entries_before = requests.get(
            f"{base_url}/journal-entries?company_id={bs.company_id}&page=1&per_page=1",
            headers=bs.auth_headers,
        )
        count_before = entries_before.json().get("total", 0)

        _gemini_request(base_url, bs.auth_headers, bs.company_id, "دفعت 300 كهرباء من البنك")

        entries_after = requests.get(
            f"{base_url}/journal-entries?company_id={bs.company_id}&page=1&per_page=1",
            headers=bs.auth_headers,
        )
        count_after = entries_after.json().get("total", 0)
        assert count_after == count_before, \
            f"Preview created an entry! Before: {count_before}, After: {count_after}"

    def test_no_generic_help_for_accounting_phrases(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        phrases = ["دفعت 300 كهربا", "استلمنا 1000", "خرجنا 300"]
        for phrase in phrases:
            resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, phrase)
            assert resp.status_code == 200
            data = resp.json()
            reply = data["reply"]
            assert "يمكنني مساعدتك في" not in reply, \
                f"Generic help menu returned for '{phrase}'. Intent: {data['intent']}"
