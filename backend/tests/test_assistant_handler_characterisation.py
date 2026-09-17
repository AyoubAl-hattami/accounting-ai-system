# -*- coding: utf-8 -*-
"""Characterisation tests for assistant handlers that no other test reaches.

These record what ``dispatch_gemini_assistant`` DOES today, not what it should
do. Measured coverage showed three dispatched intents with zero execution of
their handler bodies -- ``pl_contribution_question`` (21 statements),
``audit_question`` (13) and ``user_question`` (5). Nothing pinned their output,
so moving them was unverifiable.

Where the captured behaviour looks wrong it is captured anyway and filed as a
finding instead. Fixing a bug inside a characterisation test hides what a later
refactor changed, which is the one thing this file exists to prevent.

Deliberately recorded oddities, each with the assertion that pins it:

  * ``pl_contribution_question`` answers with ``intent="answer_journal_question"``
    -- the same intent string ``journal_question`` uses. A caller cannot tell
    the two handlers apart. Pinned by
    ``test_pl_contribution_answers_with_the_journal_question_intent``.
  * ``pl_contribution_question`` reports ``confidence="high"`` and
    ``status="grounded"`` when it found nothing, where every sibling handler
    reports ``low``. Pinned by
    ``test_pl_contribution_reports_high_confidence_for_an_empty_result``.
  * ``pl_contribution_question`` fills ``grounding.entries`` but leaves
    ``reply.evidence`` empty, unlike ``trace_question``. Pinned by
    ``test_pl_contribution_populates_grounding_but_not_evidence``.
"""
from decimal import Decimal

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import gemini_assistant_service as service


@pytest.fixture
def no_gemini(monkeypatch):
    """Pin the deterministic fallback path.

    The audit and user handlers call Gemini first and fall back only when it
    returns nothing. Without this the captured reply would depend on whether an
    API key happens to be configured.
    """
    monkeypatch.setattr(service, "_call_gemini_for_answer", lambda *a, **k: None)


def dispatch(message, role="admin", language="en", **kwargs):
    return service.dispatch_gemini_assistant(
        db=None, company_id=8, user_role=role, message=message,
        page_context=PageContext(), language=language, **kwargs,
    )


def _contributors():
    return [
        {"id": 71, "entry_no": "JE-71", "entry_date": "2026-02-10",
         "description": "Invoice 900", "status": "posted", "source_type": "manual",
         "created_by": "Sara Ahmed", "total_debit": "900.00", "total_credit": "900.00",
         "matched_amount": "900.00", "match_reason": "report_revenue_contribution"},
        {"id": 72, "entry_no": "JE-72", "entry_date": "2026-02-11",
         "description": None, "status": "posted", "source_type": "manual",
         "created_by": None, "total_debit": "100.00", "total_credit": "100.00",
         "matched_amount": "100.00", "match_reason": "report_revenue_contribution"},
    ]


def _audit_logs():
    return [
        {"action": "post_journal_entry", "actor": "Sara Ahmed",
         "entity_type": "journal_entry", "entity_id": 41,
         "created_at": "2026-03-04T09:15:00", "description": "Posted JE-41"},
        {"action": "create_journal_entry", "actor": "Omar Ali",
         "entity_type": "journal_entry", "entity_id": 42,
         "created_at": "2026-03-03T14:02:11", "description": None},
    ]


def _company_users():
    return [
        {"role": "admin", "is_active": True, "name": "Sara Ahmed", "email": "sara@x.test"},
        {"role": "viewer", "is_active": False, "name": None, "email": "old@x.test"},
    ]


# ── pl_contribution_question ─────────────────────────────────────────────────


def test_pl_contribution_answers_with_the_journal_question_intent(monkeypatch):
    """RECORDED AS-IS: this handler is not distinguishable by its intent.

    It answers "answer_journal_question", which is also what the journal_question
    handler answers. Filed, not fixed.
    """
    monkeypatch.setattr(service, "_tool_get_pl_contributors",
                        lambda *a, **k: _contributors())
    reply = dispatch("show revenue entries", role="viewer")
    assert reply.intent == "answer_journal_question"
    assert reply.confidence == "high"
    assert reply.data_sources == ["profit_loss_report", "journal_entries"]


def test_pl_contribution_revenue_reply_and_grounding_are_exact(monkeypatch):
    monkeypatch.setattr(service, "_tool_get_pl_contributors",
                        lambda *a, **k: _contributors())
    reply = dispatch("show revenue entries", role="viewer")

    assert reply.reply == (
        "I found 2 entries contributing to revenue for all available data.\n"
        "1. JE-71 | 2026-02-10 | Invoice 900 | posted | Contribution: 900.00\n"
        "2. JE-72 | 2026-02-11 | Not available | posted | Contribution: 100.00"
    )
    grounding = reply.grounding
    assert grounding.status == "grounded"
    assert grounding.kind == "journal_evidence"
    assert grounding.basis == "profit_and_loss_contribution"
    assert grounding.metric == "revenue"
    assert grounding.period.start_date is None
    assert grounding.period.end_date is None
    assert grounding.period.label == "all available data"
    assert grounding.summary.total_matches == 2
    assert grounding.summary.returned_matches == 2
    assert grounding.summary.has_more is False
    assert grounding.entries[0].entry_number == "JE-71"
    assert grounding.entries[0].creator_name == "Sara Ahmed"
    # A contributor with no creator is labelled, not blanked.
    assert grounding.entries[1].creator_name == "Not available"


def test_pl_contribution_populates_grounding_but_not_evidence(monkeypatch):
    """RECORDED AS-IS: trace_question fills reply.evidence here; this does not."""
    monkeypatch.setattr(service, "_tool_get_pl_contributors",
                        lambda *a, **k: _contributors())
    reply = dispatch("show revenue entries", role="viewer")
    assert reply.grounding.entries != []
    assert reply.evidence == []


def test_pl_contribution_expense_request_selects_the_expenses_metric(monkeypatch):
    seen = []

    def contributors(db, company_id, start_date, end_date, metric, limit=10):
        seen.append(metric)
        return _contributors()

    monkeypatch.setattr(service, "_tool_get_pl_contributors", contributors)
    reply = dispatch("show expense entries")
    assert seen == ["expenses"]
    assert reply.grounding.metric == "expenses"
    assert reply.reply.startswith(
        "I found 2 entries contributing to expenses for all available data.")


def test_pl_contribution_net_profit_queries_revenue_and_expenses_in_order(monkeypatch):
    """A net-profit follow-up runs the tool twice and merges the two results."""
    seen = []

    def contributors(db, company_id, start_date, end_date, metric, limit=10):
        seen.append((start_date.isoformat(), end_date.isoformat(), metric, limit))
        return _contributors()

    monkeypatch.setattr(service, "_tool_get_pl_contributors", contributors)
    reply = dispatch("show the entries", prior_grounding={
        "status": "grounded", "kind": "profit_and_loss",
        "metrics": {"net_profit": "1.00"},
        "period": {"start_date": "2026-01-01", "end_date": "2026-03-31",
                   "label": "Q1 2026"},
    })

    assert seen == [
        ("2026-01-01", "2026-03-31", "revenue", 10),
        ("2026-01-01", "2026-03-31", "expenses", 10),
    ]
    assert reply.grounding.metric == "net_profit"
    assert reply.grounding.period.label == "Q1 2026"
    # Both calls return the same two ids, and the handler de-duplicates by id.
    assert reply.grounding.summary.returned_matches == 2
    assert reply.reply.startswith(
        "I found 2 entries contributing to revenue and expenses for Q1 2026.")


def test_pl_contribution_ignores_a_period_it_cannot_parse(monkeypatch):
    """RECORDED AS-IS: a malformed period silently widens the query to all time."""
    seen = []

    def contributors(db, company_id, start_date, end_date, metric, limit=10):
        seen.append((start_date, end_date))
        return _contributors()

    monkeypatch.setattr(service, "_tool_get_pl_contributors", contributors)
    reply = dispatch("show the entries", prior_grounding={
        "status": "grounded", "kind": "profit_and_loss",
        "requested_metric": "revenue",
        "period": {"start_date": "not-a-date", "end_date": None, "label": None},
    })
    assert seen == [(None, None)]
    assert reply.grounding.period.label == "all available data"


def test_pl_contribution_reports_high_confidence_for_an_empty_result(monkeypatch):
    """RECORDED AS-IS: no contributors still reports high confidence and grounded.

    Every sibling handler reports "low" when it found nothing. Filed, not fixed.
    """
    monkeypatch.setattr(service, "_tool_get_pl_contributors", lambda *a, **k: [])
    reply = dispatch("show revenue entries")
    assert reply.confidence == "high"
    assert reply.grounding.status == "grounded"
    assert reply.grounding.summary.total_matches == 0
    assert reply.data_sources == ["profit_loss_report", "journal_entries"]
    assert reply.reply == (
        "No contributing journal entries were found for this report period.")


def test_pl_contribution_unavailable_tool_refuses_to_estimate(monkeypatch):
    """The tool returning None means "could not read", and is never guessed past."""
    monkeypatch.setattr(service, "_tool_get_pl_contributors", lambda *a, **k: None)
    reply = dispatch("show revenue entries")
    assert reply.intent == "answer_journal_question"
    assert reply.confidence == "low"
    assert reply.data_sources == []
    assert reply.grounding.status == "unavailable"
    assert reply.grounding.kind == "journal_evidence"
    assert reply.reply == (
        "I could not verify the journal entries from the accounting data. "
        "No estimated results were shown.")


# ── audit_question ───────────────────────────────────────────────────────────


def test_audit_question_reply_is_the_deterministic_fallback(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    reply = dispatch("Show the audit log")

    assert reply.intent == "answer_audit_question"
    assert reply.confidence == "high"
    assert reply.data_sources == ["audit_logs"]
    assert reply.grounding is None
    assert reply.reply == (
        "📋 **Recent Audit Activity:**\n"
        "\n"
        "• **Sara Ahmed** — post journal entry — 2026-03-04\n"
        "  _Posted JE-41_\n"
        "• **Omar Ali** — create journal entry — 2026-03-03"
    )


def test_audit_question_prefers_gemini_over_the_fallback(monkeypatch):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    monkeypatch.setattr(service, "_call_gemini_for_answer",
                        lambda *a, **k: "Gemini wrote this.")
    reply = dispatch("Show the audit log")
    assert reply.reply == "Gemini wrote this."
    assert reply.confidence == "high"
    assert reply.data_sources == ["audit_logs"]


def test_audit_question_with_no_logs_drops_to_low_confidence(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", lambda *a, **k: [])
    reply = dispatch("Show the audit log")
    assert reply.confidence == "low"
    assert reply.data_sources == ["audit_logs"]
    assert reply.reply == "No audit log entries found."


@pytest.mark.parametrize(("message", "expected_filter"), [
    ("Show the audit log", None),
    ("Show the audit trail", None),
    ("Show the audit log for role changes", "update_company_user"),
    ("Audit history for posted entries", "post_journal_entry"),
    ("Audit log of created records", "create_journal_entry"),
])
def test_audit_question_derives_its_action_filter_from_the_message(
    monkeypatch, no_gemini, message, expected_filter,
):
    seen = []

    def logs(db, company_id, action=None, limit=10):
        seen.append((action, limit))
        return _audit_logs()

    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", logs)
    dispatch(message)
    assert seen == [(expected_filter, 10)]


@pytest.mark.parametrize("role", ["admin", "auditor"])
def test_audit_question_is_answered_for_permitted_roles(monkeypatch, no_gemini, role):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    assert dispatch("Show the audit log", role=role).intent == "answer_audit_question"


@pytest.mark.parametrize("role", ["accountant", "reviewer", "approver", "viewer"])
def test_audit_question_is_refused_for_every_other_role(monkeypatch, no_gemini, role):
    def refuse(*a, **k):
        raise AssertionError("audit logs must not be read for a denied role")

    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", refuse)
    reply = dispatch("Show the audit log", role=role)
    assert reply.intent == "access_denied"
    assert reply.confidence == "high"
    assert reply.data_sources == []
    assert reply.reply == "🔒 You don't have permission to access audit logs."


def test_audit_question_refusal_is_translated(monkeypatch, no_gemini):
    """The Arabic route in is "last activity", not "audit".

    The audit keyword list carries no Arabic word for audit at all, so the
    obvious phrasing does not reach this handler. Filed, not fixed.
    """
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", lambda *a, **k: [])
    assert service._classify_intent("اعرض سجل التدقيق") == "unknown"

    reply = dispatch("اعرض آخر نشاط", role="viewer", language="ar")
    assert reply.intent == "access_denied"
    assert reply.reply == "🔒 ليس لديك صلاحية الوصول إلى سجلات التدقيق."


def test_audit_question_answers_in_arabic(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", lambda *a, **k: [])
    reply = dispatch("اعرض آخر نشاط", role="admin", language="ar")
    assert reply.intent == "answer_audit_question"
    assert reply.reply == "لم يتم العثور على سجلات تدقيق."


# ── user_question ────────────────────────────────────────────────────────────


def test_user_question_reply_is_the_deterministic_fallback(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_company_users",
                        lambda *a, **k: _company_users())
    reply = dispatch("List the users")

    assert reply.intent == "answer_user_question"
    assert reply.confidence == "high"
    assert reply.data_sources == ["company_users"]
    assert reply.grounding is None
    # A user with no full name is listed by email, and inactive users come first.
    assert reply.reply == (
        "👥 **Users: 2 (Active: 1 | Inactive: 1)**\n"
        "\n"
        "**Inactive:**\n"
        "  - old@x.test (viewer)\n"
        "\n"
        "**Active:**\n"
        "  - Sara Ahmed (admin)"
    )


def test_user_question_prefers_gemini_over_the_fallback(monkeypatch):
    monkeypatch.setattr(service, "_tool_get_company_users",
                        lambda *a, **k: _company_users())
    monkeypatch.setattr(service, "_call_gemini_for_answer",
                        lambda *a, **k: "Gemini wrote this.")
    assert dispatch("List the users").reply == "Gemini wrote this."


def test_user_question_with_no_users_drops_to_low_confidence(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_company_users", lambda *a, **k: [])
    reply = dispatch("List the users")
    assert reply.confidence == "low"
    assert reply.data_sources == ["company_users"]
    assert reply.reply == "No users found."


@pytest.mark.parametrize("role", ["admin", "auditor"])
def test_user_question_is_answered_for_permitted_roles(monkeypatch, no_gemini, role):
    monkeypatch.setattr(service, "_tool_get_company_users",
                        lambda *a, **k: _company_users())
    assert dispatch("List the users", role=role).intent == "answer_user_question"


@pytest.mark.parametrize("role", ["accountant", "reviewer", "approver", "viewer"])
def test_user_question_is_refused_for_every_other_role(monkeypatch, no_gemini, role):
    def refuse(*a, **k):
        raise AssertionError("company users must not be read for a denied role")

    monkeypatch.setattr(service, "_tool_get_company_users", refuse)
    reply = dispatch("List the users", role=role)
    assert reply.intent == "access_denied"
    assert reply.confidence == "high"
    assert reply.data_sources == []
    assert reply.reply == "🔒 You don't have permission to view company user data."

# ── who_action_question ──────────────────────────────────────────────

# The whole discriminating logic of this handler is a chain of substring tests
# that picks one audit action to filter by. Four of its six arms were never
# executed by any test, so the chain could have been reordered or dropped
# without a single failure. Each arm is pinned here, in both languages where
# the classifier offers a route in.


def _who_action_filter(monkeypatch, message, role="admin", language="en"):
    """Return the action filter this message causes, and the reply."""
    seen = []

    def logs(db, company_id, action=None, limit=10):
        seen.append((action, limit))
        return []

    monkeypatch.setattr(service, "_tool_get_recent_audit_logs", logs)
    reply = dispatch(message, role=role, language=language)
    assert reply.intent == "answer_who_action_question"
    assert len(seen) == 1
    return seen[0][0], reply


@pytest.mark.parametrize(("message", "expected_filter"), [
    ("Who posted the entry?", "post_journal_entry"),
    ("Who reviewed the entry?", "review_journal_entry"),
    ("Who created the entry?", "create_journal_entry"),
    ("Who made the reverse entry?", "reverse_journal_entry"),
    ("Who changed the role?", "update_company_user"),
    ("Who modified it?", "update_company_user"),
    ("Who deleted the user?", "remove_company_access"),
    ("who made the call", None),
])
def test_who_action_english_arms_select_their_audit_action(
    monkeypatch, no_gemini, message, expected_filter,
):
    assert _who_action_filter(monkeypatch, message)[0] == expected_filter


@pytest.mark.parametrize(("message", "expected_filter"), [
    ("من رحل القيد", "post_journal_entry"),
    ("من راجع القيد", "review_journal_entry"),
    ("من أنشأ القيد", "create_journal_entry"),
    ("من عدل الصلاحية", "update_company_user"),
    ("من حذف المستخدم", "remove_company_access"),
])
def test_who_action_arabic_arms_select_their_audit_action(
    monkeypatch, no_gemini, message, expected_filter,
):
    assert _who_action_filter(monkeypatch, message, language="ar")[0] == expected_filter


def test_who_action_arms_are_ordered_and_the_first_match_wins(monkeypatch, no_gemini):
    """The chain is elif, so a message naming two actions gets the earlier arm."""
    assert _who_action_filter(
        monkeypatch, "Who posted and reviewed the entry?")[0] == "post_journal_entry"
    assert _who_action_filter(
        monkeypatch, "Who reviewed and deleted it?")[0] == "review_journal_entry"


def test_who_action_reverse_arm_has_no_route_of_its_own(monkeypatch, no_gemini):
    """RECORDED AS-IS: the classifier has no "who reversed" pattern.

    "Who reversed the entry?" is classified audit_question, not
    who_action_question -- it reaches this handler only because the intent
    orchestrator re-routes it. The reverse arm is therefore reachable from the
    classifier only by a message that matches some OTHER who-action pattern and
    happens to contain the word "reverse". Filed, not fixed.
    """
    assert service._classify_intent("Who reversed the entry?") == "audit_question"
    assert service._classify_intent("Who made the reverse entry?") == "who_action_question"

    # Routed to who_action anyway, by the orchestrator rather than the classifier.
    action, reply = _who_action_filter(monkeypatch, "Who reversed the entry?")
    assert action == "reverse_journal_entry"
    assert reply.intent == "answer_who_action_question"


def test_who_action_unmatched_message_reports_recent_actions(monkeypatch, no_gemini):
    """With no arm matched, the filter is None and the reply says so."""
    action, reply = _who_action_filter(monkeypatch, "who made the call")
    assert action is None
    assert reply.confidence == "low"
    assert reply.data_sources == ["audit_logs"]
    assert reply.reply == "🔍 No audit log found matching 'recent actions'."


def test_who_action_empty_result_names_the_filter_it_used(monkeypatch, no_gemini):
    _, reply = _who_action_filter(monkeypatch, "Who reviewed the entry?")
    assert reply.reply == (
        "🔍 No audit log found matching 'review_journal_entry'.")

    _, arabic = _who_action_filter(
        monkeypatch, "من راجع القيد", language="ar")
    assert arabic.reply == (
        "🔍 لم أجد سجل تدقيق يطابق 'review_journal_entry'.")


def test_who_action_reply_leads_with_the_latest_log(monkeypatch, no_gemini):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    reply = dispatch("Who reviewed the entry?")

    assert reply.confidence == "high"
    assert reply.data_sources == ["audit_logs"]
    assert reply.grounding is None
    # RECORDED AS-IS: the reply describes the newest log whatever the filter
    # asked for -- the handler does not check that the log it found matches.
    assert reply.reply == (
        "👤 **Sara Ahmed** performed **post journal entry** "
        "at 2026-03-04T09:15:00.\n"
        "• Description: Posted JE-41\n"
        "\n"
        "📋 **Last 2 actions:**\n"
        "• Sara Ahmed — post journal entry — 2026-03-04T09:15:00\n"
        "• Omar Ali — create journal entry — 2026-03-03T14:02:11"
    )


def test_who_action_prefers_gemini_over_the_fallback(monkeypatch):
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    monkeypatch.setattr(service, "_call_gemini_for_answer",
                        lambda *a, **k: "Gemini wrote this.")
    assert dispatch("Who reviewed the entry?").reply == "Gemini wrote this."


def test_who_action_shares_the_audit_log_role_gate(monkeypatch, no_gemini):
    """This handler reads audit logs and carries the audit gate, at line 3701.

    Written first as "not gated", which the run corrected: who_action_question
    is restricted to the same _CAN_READ_AUDIT_LOGS roles as audit_question, and
    refuses with the audit-log wording.
    """
    monkeypatch.setattr(service, "_tool_get_recent_audit_logs",
                        lambda *a, **k: _audit_logs())
    for role in ("admin", "auditor"):
        assert dispatch("Who reviewed the entry?", role=role).intent == (
            "answer_who_action_question")

    for role in ("accountant", "reviewer", "approver", "viewer"):
        reply = dispatch("Who reviewed the entry?", role=role)
        assert reply.intent == "access_denied"
        assert reply.data_sources == []
        assert reply.reply == "🔒 You don't have permission to access audit logs."

# ── trace_question ───────────────────────────────────────────────────

# Two whole arms of this handler were unexercised: the amount-not-identified
# clarification (3809-3819) and the refusal to estimate when the journal cannot
# be read (3822-3823).


def _trace(monkeypatch, message, matches, language="en"):
    monkeypatch.setattr(service, "_tool_trace_amount", lambda *a, **k: matches)
    return dispatch(message, language=language)


def test_trace_treats_zero_as_an_unidentifiable_amount(monkeypatch):
    """RECORDED AS-IS: asking about 0 is answered "I couldn't identify the amount".

    This is the only English route into the clarification arm. _classify_intent
    returns trace_question because the message contains a digit, and then
    _extract_amount_from_message returns None for zero, so the two disagree.
    Filed, not fixed.
    """
    assert service._classify_intent("who entered 0?") == "trace_question"
    assert service._extract_amount_from_message("who entered 0?") is None
    assert service._extract_amount_from_message("who entered 0.00?") is None

    reply = _trace(monkeypatch, "who entered 0?", [])
    assert reply.intent == "clarification"
    assert reply.confidence == "low"
    assert reply.data_sources == []
    assert reply.grounding is None
    assert reply.reply == (
        "🤔 I couldn't identify the amount. "
        "Please specify, e.g. 'Who entered 1000?'")


def test_trace_clarification_is_arabic_for_an_arabic_question(monkeypatch):
    """The Arabic route in needs no digits at all, unlike every other one."""
    assert service._classify_intent(
        "وين راحت الفلوس؟") == "trace_question"

    reply = _trace(monkeypatch, "وين راحت الفلوس؟", [], language="ar")
    assert reply.intent == "clarification"
    assert reply.reply == (
        "🤔 لم أتمكن من تحديد المبلغ. "
        "حدد المبلغ المطلوب تتبعه، مثل: "
        "'من أدخل 1000؟'")


def test_trace_language_argument_loses_to_the_message(monkeypatch):
    """RECORDED AS-IS: language="en" still answers in Arabic here.

    dispatch_gemini_assistant re-detects the language from the message at line
    3434, so the caller's choice is advisory.
    """
    english_request = _trace(
        monkeypatch, "وين راحت الفلوس؟", [], language="en")
    arabic_request = _trace(
        monkeypatch, "وين راحت الفلوس؟", [], language="ar")
    assert english_request.reply == arabic_request.reply


def test_trace_unavailable_journal_refuses_to_estimate(monkeypatch):
    """The tool returning None means "could not read", and is never guessed past."""
    reply = _trace(monkeypatch, "Who entered 1000?", None)
    assert reply.intent == "answer_trace_question"
    assert reply.confidence == "low"
    assert reply.data_sources == []
    assert reply.grounding.status == "unavailable"
    assert reply.grounding.kind == "journal_evidence"
    assert reply.evidence == []
    assert reply.reply == (
        "I could not verify the journal entries from the accounting data. "
        "No estimated results were shown.")


def test_trace_empty_result_is_not_the_same_as_an_unreadable_one(monkeypatch):
    """Nothing found is medium confidence and still grounded; unreadable is low."""
    reply = _trace(monkeypatch, "Who entered 1000?", [])
    assert reply.intent == "answer_trace_question"
    assert reply.confidence == "medium"
    assert reply.data_sources == ["journal_entries"]
    assert reply.reply == (
        "No journal entries matching 1,000.00 were found in the current "
        "company data.")


def test_trace_match_populates_both_evidence_and_grounding(monkeypatch):
    matches = [{
        "id": 71, "entry_no": "JE-71", "entry_date": "2026-02-10",
        "description": "Invoice 900", "status": "posted", "source_type": "manual",
        "created_by": "Sara Ahmed", "amount": "1000.00", "total_debit": "1000.00",
        "total_credit": "1000.00", "matched_amount": "1000.00",
        "match_reason": "debit_line", "debit_accounts": ["1100 Cash"],
        "credit_accounts": ["4000 Revenue"],
    }]
    reply = _trace(monkeypatch, "Who entered 1000?", matches)

    assert reply.confidence == "high"
    # Audit logs join the sources only when something matched.
    assert reply.data_sources == ["journal_entries", "audit_logs"]
    assert len(reply.evidence) == 1
    assert reply.evidence[0].entry_no == "JE-71"
    assert reply.evidence[0].debit_account == "1100 Cash"
    assert reply.evidence[0].credit_account == "4000 Revenue"
    assert reply.grounding.status == "grounded"
    assert reply.grounding.summary.total_matches == 1
    assert reply.reply == (
        "I found 1 journal entries containing 1,000.00.\n"
        "1. JE-71 | 2026-02-10 | Invoice 900 | posted | Debit amount 1,000.00")

def test_trace_answers_a_negative_amount_as_its_positive(monkeypatch):
    """RECORDED AS-IS: the sign is not read, so -5 is answered as 5.

    _extract_amount_from_message scans for unsigned tokens only -- its pattern
    has no sign, and its docstring says "positive" -- so a question about a
    negative figure is silently answered about the positive one. The reply says
    5.00 and never mentions that it changed what was asked. Filed, not fixed.
    """
    assert service._extract_amount_from_message("who entered -5?") == Decimal("5")
    assert service._extract_amount_from_message(
        "who entered -1000.50?") == Decimal("1000.50")
    assert service._extract_amount_from_message(
        "من أدخل -5؟") == Decimal("5")

    asked = []

    def trace(db, company_id, amount, account_hint):
        asked.append(amount)
        return []

    monkeypatch.setattr(service, "_tool_trace_amount", trace)
    reply = dispatch("who entered -5?")

    assert asked == [Decimal("5")]
    assert reply.intent == "answer_trace_question"
    assert reply.reply == (
        "No journal entries matching 5.00 were found in the current "
        "company data.")
    assert "-5" not in reply.reply
