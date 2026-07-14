# -*- coding: utf-8 -*-
"""Focused Phase 2 journal evidence tests. Not executed during implementation."""

from decimal import Decimal

from app.modules.accounting.services.gemini_assistant_service import (
    _build_journal_evidence,
    _deterministic_trace_reply,
    _extract_amount_from_message,
    _is_exact_amount_trace_request,
)


def test_amount_parser_is_decimal_safe():
    assert _extract_amount_from_message("SAR 1,000.00") == Decimal("1000.00")
    assert _extract_amount_from_message("$1000") == Decimal("1000")
    assert _extract_amount_from_message("1000") == Decimal("1000")
    assert _extract_amount_from_message("0") is None


def test_arabic_and_english_trace_routing_regression():
    assert _is_exact_amount_trace_request("من أين جاء مبلغ 1000؟")
    assert _is_exact_amount_trace_request("من أين جاء مبلغ $1000؟")
    assert _is_exact_amount_trace_request("ابحث عن مبلغ 1000")
    assert _is_exact_amount_trace_request("أين يوجد مبلغ 1000؟")
    assert _is_exact_amount_trace_request("اعرض القيود التي فيها 1000")
    assert _is_exact_amount_trace_request("Where did the amount $1000 come from?")
    assert _is_exact_amount_trace_request("Find entries containing 1000")


def test_journal_evidence_has_bounded_safe_metadata():
    matches = [{
        "id": 10,
        "entry_no": "JE-1",
        "entry_date": "2026-07-13",
        "description": "Rent",
        "status": "posted",
        "source_type": "manual",
        "created_by": "Admin",
        "total_debit": "1000.00",
        "total_credit": "1000.00",
        "match_reason": "debit_line",
    }]
    grounding = _build_journal_evidence(matches, Decimal("1000.00"))
    assert grounding.status == "grounded"
    assert grounding.summary.returned_matches == 1
    assert grounding.entries[0].matched_amount == "1000.00"
    assert not hasattr(grounding, "company_id")
    assert not hasattr(grounding, "url")


def test_empty_search_is_grounded_and_deterministic():
    reply = _deterministic_trace_reply([], Decimal("999999.00"), "en")
    assert "No journal entries matching 999,999.00" in reply


def test_arabic_indic_and_persian_amounts_normalize_without_float():
    assert _extract_amount_from_message("١٬٠٠٠") == Decimal("1000")
    assert _extract_amount_from_message("١٬٠٠٠٫٥٠") == Decimal("1000.50")
    assert _extract_amount_from_message("۱٬۰۰۰٫۵۰") == Decimal("1000.50")
    assert _extract_amount_from_message("1,000.50") == Decimal("1000.50")


def test_malformed_separators_are_rejected():
    assert _extract_amount_from_message("1,00,0") is None
    assert _extract_amount_from_message("١٬٠٠") is None


def test_trace_phrases_with_unicode_amounts_are_supported():
    assert _is_exact_amount_trace_request("من أين جاء مبلغ ١٬٠٠٠؟")
    assert _is_exact_amount_trace_request("من أين جاء مبلغ ۱٬۰۰۰٫۵۰؟")


def test_unicode_separator_codepoints_are_preserved():
    assert "\u066c" in "١٬٠٠٠"
    assert "\u066b" in "١٬٠٠٠٫٥٠"

def test_persisted_profit_loss_grounding_validates_requested_metric():
    from app.modules.accounting.schemas.gemini_assistant_schemas import ProfitAndLossGrounding
    grounding = ProfitAndLossGrounding.model_validate({
        "status": "grounded",
        "kind": "profit_and_loss",
        "requested_metric": "net_profit",
        "period": {"label": "all available data"},
        "metrics": {"revenue": "5000.00", "expenses": "2800.00", "net_profit": "2200.00"},
        "reference": {"type": "report", "report": "profit_and_loss", "filters": {}},
    })
    assert grounding.requested_metric == "net_profit"


def test_malformed_or_non_profit_grounding_is_not_valid_context():
    from app.modules.accounting.schemas.gemini_assistant_schemas import ProfitAndLossGrounding
    import pytest
    with pytest.raises(Exception):
        ProfitAndLossGrounding.model_validate({"status": "grounded", "kind": "journal_evidence"})


def test_bare_show_entries_is_distinct_from_explicit_recent_request():
    from app.modules.accounting.services.gemini_assistant_service import _is_generic_entries_request
    assert _is_generic_entries_request("اعرض القيود")
    assert _is_generic_entries_request("Show the entries")
    assert not _is_generic_entries_request("اعرض آخر القيود")
    assert not _is_generic_entries_request("Show recent journal entries")
