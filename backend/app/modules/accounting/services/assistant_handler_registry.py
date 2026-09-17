"""Scaffolding for moving assistant handlers out of the dispatcher's if-chain.

``dispatch_gemini_assistant`` resolves an intent through a five-step override
chain and then runs a ~290-line chain of ``if intent == ...`` branches. The
gates that authorise those branches sit up to 300 lines above them, and a
handler appended below the gates receives no authorization check. That is not
hypothetical -- ``pl_contribution_question`` shipped that way.

This module holds the data the migration moves handlers INTO. It is deliberately
empty at this commit: ``ASSISTANT_HANDLERS`` is ``()``, the dispatcher still runs
its if-chain, and the loop that consults this registry is a no-op.

WHAT THE REGISTRY KEYS ON
-------------------------
The final value of the dispatcher's local ``intent``, after the whole override
chain has run -- NOT ``_classify_intent``'s return value. The chain, in order:

  1. 3608  _is_exact_amount_trace_request -> "trace_question", else _classify_intent
  2. 3633  handler_to_legacy_intent[intent_decision.target_handler]
  3. 3643  structured_kind set -> "structured_report_question"
  4. 3646  contribution_metric set -> "pl_contribution_question"
  5. 3647  "unknown" + looks like an amount -> "action_request"

Each step wins over the ones above it. ``pl_contribution_question`` is produced
ONLY by step 4, so a registry keyed on the classifier or on ``target_handler``
would never dispatch it. Intent RESOLUTION stays in the dispatcher; this
registry replaces only what happens after it.

WHERE THE LOOP SITS, AND WHY IT IS NOT AT THE TOP OF THE CHAIN
--------------------------------------------------------------
Two branches that do not test ``intent`` sit INSIDE the chain:
``if structured_followup:`` (3734) and ``if generic_without_context:`` (3741).
A loop placed before the chain would run every registered handler ahead of both.

Measured over 1,323 messages x 2 languages x 4 grounding states, reading the
dispatcher's locals at the first gate, four states reach the chain with one of
those flags set and a dispatched intent:

    journal_question            generic_without_context=True
    journal_question            structured_followup=True
    report_question             structured_followup=True
    structured_report_question  structured_followup=True

So those two branches really do preempt those handlers today, and the loop must
sit AFTER line 3741. It does.

The consequence is that ``pl_contribution_question`` -- the only dispatched
intent whose branch is ABOVE 3734 -- cannot be registered through this loop
without moving it past two branches that currently precede it. It was never
measured co-occurring with either flag, and ``generic_without_context`` is
False whenever ``contribution_metric`` is set by construction (3610), but
``structured_followup`` carries no such guarantee. It stays inline until that is
proven or a second loop is added at its position.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.orm import Session

    from app.modules.accounting.schemas.gemini_assistant_schemas import (
        ConversationTurn,
        GeminiAssistantReply,
        PageContext,
    )
    from app.modules.accounting.services.gemini_agent_contract import (
        AgentRuntimeContext,
    )


# ── Permission vocabulary ───────────────────────────────────────
# These live here rather than in the service because a registry entry has to
# name the set that gates it, and the service already imports this module -- so
# the service cannot own them without a cycle. They are imported back into the
# service under the same names, so every gate there reads exactly as it did.
#
# A copy in each place would NOT be caught by the consistency test:
# _CAN_READ_USERS and _CAN_READ_AUDIT_LOGS are equal today, so a stale copy of
# one would still compare equal to the other and pass. One definition removes
# the question.
_CAN_READ_REPORTS = frozenset(
    {"admin", "accountant", "reviewer", "approver", "auditor", "viewer"})
_CAN_READ_AUDIT_LOGS = frozenset({"admin", "auditor"})
_CAN_READ_USERS = frozenset({"admin", "auditor"})
_CAN_CREATE_DRAFT = frozenset({"admin", "accountant"})

@dataclass(frozen=True, slots=True)
class AssistantRequest:
    """Every dispatcher local a handler body reads, passed through unchanged.

    The field list is not a design: it is the measured union of the names the
    ten handler bodies load from the dispatcher's scope, plus ``intent``, which
    the guards read. Nothing here is derived, defaulted, renamed or recomputed
    -- each field carries the exact value of the identically named local at the
    point the loop runs, so moving a handler is a move and not a rewrite.

    ``language`` in particular is the REASSIGNED value from line 3434
    (``detect_message_language(message, language)``), not the caller's argument,
    because that is what the handler bodies read today.

    ``structured_followup`` is deliberately absent: no handler body reads it. It
    is consumed by the branch at 3734, which is not a registry entry.
    """

    db: Session | None
    company_id: int
    user_role: str
    message: str
    language: str
    intent: str
    page_context: PageContext
    history: list[ConversationTurn] | None
    runtime_context: AgentRuntimeContext
    prior_grounding: dict[str, Any] | None
    structured_kind: str | None
    contribution_metric: str | None
    orchestrated_account_target: str | None


@dataclass(frozen=True, slots=True)
class Denial:
    """The reply text a refusal returns, in both languages.

    The dispatcher has five distinct refusal texts and they are not
    interchangeable, so each entry names its own rather than sharing a default.

    Only the text varies. All five refusals return the same envelope --
    ``intent="access_denied"``, ``confidence="high"``, ``data_sources=[]`` --
    and the loop builds that, not this.

    One of the five (the structured-report gate at 3884) writes its language
    test inverted, as ``english if language != "ar" else arabic``, and omits the
    lock emoji every other refusal carries. The inversion is cosmetic: it
    selects the same string as the others for every input. The missing emoji is
    not, and is preserved by storing the text verbatim.
    """

    arabic: str
    english: str

    def reply_for(self, language: str) -> str:
        return self.arabic if language == "ar" else self.english


@dataclass(frozen=True, slots=True)
class ServiceHandler:
    """Names a handler function in gemini_assistant_service, resolved when called.

    The service imports this module, so this module cannot import the service at
    module scope. Importing inside the call breaks the cycle, and keeps this
    module light enough for the consistency test to read the registry without
    pulling in the service, sqlalchemy and settings.

    Resolving by name at call time also keeps the existing tests honest: they
    monkeypatch attributes on the service module, and a reference captured at
    import would freeze the pre-patch function.
    """

    name: str

    def __call__(self, request: "AssistantRequest") -> "GeminiAssistantReply":
        from app.modules.accounting.services import gemini_assistant_service

        return getattr(gemini_assistant_service, self.name)(request)

@dataclass(frozen=True, slots=True)
class HandlerEntry:
    """One dispatched intent, bound to the gate that authorises it.

    Binding them in one record is the point of the refactor: the gate cannot be
    300 lines away from the handler if it is a field of it, and a handler cannot
    be added without one because ``permission`` has no default.

    ``precondition`` exists for ``structured_report_question`` alone, whose
    branch carries a second conjunct beyond the intent test. Measurement says
    that conjunct is redundant -- every path that sets the intent also sets
    ``structured_kind`` to one of the four values it accepts -- but it is
    carried verbatim anyway, so that moving the handler is provably a
    relocation. Removing it is a separate decision with its own evidence.
    """

    intents: tuple[str, ...]
    permission: frozenset[str]
    denial: Denial
    handler: Callable[[AssistantRequest], GeminiAssistantReply]
    precondition: Callable[[AssistantRequest], bool] | None = None

    def matches(self, request: AssistantRequest) -> bool:
        if request.intent not in self.intents:
            return False
        return self.precondition is None or self.precondition(request)


# Handlers are appended one commit at a time; the consistency test in
# tests/test_assistant_handler_gate_coverage.py holds the invariant that every
# producible intent is dispatched exactly once, inline or from here.
ASSISTANT_HANDLERS: tuple[HandlerEntry, ...] = (
    HandlerEntry(
        intents=("user_question",),
        permission=_CAN_READ_USERS,
        denial=Denial(
            arabic='🔒 ليس لديك صلاحية عرض بيانات المستخدمين.',
            english="🔒 You don't have permission to view company user data.",
        ),
        handler=ServiceHandler("_handle_user_question"),
    ),
    HandlerEntry(
        intents=('audit_question',),
        permission=_CAN_READ_AUDIT_LOGS,
        denial=Denial(
            arabic='🔒 ليس لديك صلاحية الوصول إلى سجلات التدقيق.',
            english="🔒 You don't have permission to access audit logs.",
        ),
        handler=ServiceHandler('_handle_audit_question'),
    ),
    HandlerEntry(
        intents=('who_action_question',),
        permission=_CAN_READ_AUDIT_LOGS,
        denial=Denial(
            arabic='🔒 ليس لديك صلاحية الوصول إلى سجلات التدقيق.',
            english="🔒 You don't have permission to access audit logs.",
        ),
        handler=ServiceHandler('_handle_who_action_question'),
    ),
    HandlerEntry(
        intents=('journal_question',),
        permission=_CAN_READ_REPORTS,
        denial=Denial(
            arabic='🔒 ليس لديك صلاحية الوصول إلى هذه البيانات.',
            english="🔒 You don't have permission to access this data.",
        ),
        handler=ServiceHandler('_handle_journal_question'),
    ),
    HandlerEntry(
        intents=('explain_question',),
        permission=_CAN_READ_REPORTS,
        denial=Denial(
            arabic='🔒 ليس لديك صلاحية الوصول إلى هذه البيانات.',
            english="🔒 You don't have permission to access this data.",
        ),
        handler=ServiceHandler('_handle_explain_question'),
    ),
)
