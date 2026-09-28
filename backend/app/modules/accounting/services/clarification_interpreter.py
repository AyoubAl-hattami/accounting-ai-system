"""Read a clarification reply the detector refused to hand to a pattern.

WHERE THIS SITS
---------------
``clarification_ambiguity`` decides whether a reply is safe for a substring
scan. Everything it clears resolves instantly and for free, exactly as
before. Everything it escalates arrives here, and before this module existed
an escalated reply got "I did not understand" -- correct, but useless to
someone who had just named a real account.

WHAT IT MAY AND MAY NOT DECIDE
------------------------------
It proposes a FIELD VALUE. It never proposes a journal line, an account id,
an amount it was not given or told to replace, a role, or a permission.

Account references come back as a CODE, and only a code that was in the chart
we sent. That code is then translated to the account's name and handed to
``map_to_accounts``, which resolves it against the live chart exactly as it
resolves a hint the deterministic parser produced. The caller then checks
that what came back is the account the interpreter named, and refuses the
draft if it is not. A hallucinated, stale or cross-company code therefore
fails twice before it can reach a ledger line, and the second check is the
one that does not depend on anything the model said.

EVERY FAILURE IS THE SAME FAILURE
---------------------------------
Provider missing, key absent, budget spent, malformed JSON, schema
violation, unknown variant, a code that is not in the chart, low confidence
on something that would write -- all of them return ``None``, and ``None``
means the caller does what it did before this module existed. There is no
degraded interpretation: either the reply was understood well enough to act
on, or the user is asked again. That is the same contract every other
model-backed stage in this service follows, and it is why the deterministic
path is not a fallback bolted on but the resting state.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.modules.accounting.services.ai_providers.gemini_provider import (
    REQUEST_TIMEOUT_SECONDS as GEMINI_REQUEST_TIMEOUT_SECONDS,
    model_calls_enabled,
    remaining_budget_seconds,
)
from app.modules.accounting.services.gemini_agent_contract import (
    AGENT_CONTRACT_VERSION,
    AgentRuntimeContext,
    build_agent_prompt,
    default_runtime_context,
)

logger = logging.getLogger(__name__)

# Fields a reply may FILL -- the ones a clarification question can ask about.
#
# This used to include "supplier_or_expense" and "customer_or_income". Nothing
# produces either name -- confirmed by a static enumeration of every call that
# can write a pending envelope's missing_fields across the app tree, and by a
# runtime spy over the whole suite -- so they widened what a model reply could
# fill without ever authorising anything. See RAG-21.
FILLABLE_FIELDS = frozenset({
    "payment_source", "receiving_account", "transaction_type",
})

# Fields a reply may REPLACE -- things already captured that a correction can
# overturn. Deliberately narrower than "anything on the transaction": a reply
# may not invent a company, a date in a closed period, or a counterparty the
# draft never had.
REPLACEABLE_FIELDS = frozenset({"amount", "payment_source", "receiving_account"})

# What a concept-valued field may be set to. An account is named by code, not
# by one of these, so this list never has to grow with the chart.
CONCEPT_VALUES = frozenset({
    "bank", "cash",
    "supplier_payment", "expense_payment", "customer_receipt", "income_receipt",
})

_QUESTION_LIMIT = 300

# The contract the model is shown, and the contract this module enforces on
# the way back. One definition, so the prompt cannot promise something the
# validator would reject.
FIXED_OUTPUT_CONTRACT: dict[str, Any] = {
    "variants": {
        "fill": "the reply answers the question; set one missing field",
        "replace": "the reply corrects something already captured",
        "abandon": "the reply calls the whole transaction off",
        "unclear": "the reply cannot be acted on; ask ONE focused question",
        "out_of_scope": "the reply changed the subject entirely",
    },
    "fillable_fields": sorted(FILLABLE_FIELDS),
    "replaceable_fields": sorted(REPLACEABLE_FIELDS),
    "concept_values": sorted(CONCEPT_VALUES),
    "account_code_rule": (
        "To name an account, return its code in account_code. The code MUST "
        "appear in current_company_chart_of_accounts. Never invent a code, "
        "never return an account name, never return a code from memory."
    ),
    "question_rule": (
        "For unclear, 'question' is plain prose in the user's language. It "
        "offers no numbered options, no menu, and names no account the chart "
        "does not contain."
    ),
    "polarity_rule": (
        "Read negation. 'not the bank, from the cash box' means CASH. If the "
        "reply rules something out without naming a replacement, that is "
        "unclear, not a guess."
    ),
    # Spelled out because the first live run did not have it: the model
    # answered correctly but called the field "concept_value", which this
    # schema does not have, so a right answer arrived as an empty one. Naming
    # the keys is cheaper than guessing at synonyms forever -- though the
    # validator accepts that one alias too, because it was observed.
    "output_keys": {
        "variant": "one of the variants above",
        "field": "the field being filled or replaced",
        "value": "a concept value, when the answer is a concept and not an account",
        "account_code": "a code from current_company_chart_of_accounts",
        "amount": "only for replace",
        "question": "only for unclear",
        "confidence": "high | medium | low",
    },
}

TASK_INSTRUCTIONS = """
Interpret ONE reply to ONE clarification question about a pending accounting
transaction. Return a single JSON object matching the fixed contract supplied
as data.

You are reading the reply only. Do not compute totals, choose journal lines,
authorise anything, or decide who may see what. Those are settled by the
backend after you answer.

Return JSON only, with no markdown and no commentary.
"""


class InterpretedReply(BaseModel):
    """What the model proposes. Validated before any of it is believed."""

    variant: Literal["fill", "replace", "abandon", "unclear", "out_of_scope"]
    field: str | None = None
    value: str | None = None
    account_code: str | None = None
    amount: float | None = None
    question: str | None = None
    # Defaults to medium, not low, and the difference matters.
    #
    # The first live run omitted this key entirely. With a "low" default that
    # made every correct fill fail the confidence gate below and fall back to
    # the re-ask -- a right answer discarded because the model did not
    # volunteer a self-assessment.
    #
    # "low" now means the model SAID it was unsure, which is worth acting on.
    # Silence is not evidence of doubt. The guards that actually protect the
    # ledger are the chart-membership check and the map_to_accounts
    # re-resolution, and neither depends on this field.
    confidence: Literal["high", "medium", "low"] = "medium"
    reason: str | None = Field(default=None, max_length=200)


def _chart_for_prompt(accounts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "code": str(a.get("code") or ""),
            "name": str(a.get("name") or ""),
            "account_type": a.get("account_type"),
            "account_subtype": a.get("account_subtype"),
        }
        for a in accounts
        if a.get("is_active", True) and a.get("code")
    ]


def _clean_question(question: str | None, codes: set[str]) -> str | None:
    """A free-form question, bounded and stripped of anything to match against.

    Free-form is the point -- a fixed set of follow-ups is the same closed
    vocabulary one layer up, which is the failure being removed. So this does
    not constrain the WORDING. It constrains length, control characters, and
    the one thing a free-form question must still not do: name an account code
    that is not in this company's chart.
    """
    if not question:
        return None
    text = " ".join(str(question).split())
    text = "".join(character for character in text if character.isprintable())
    if not text:
        return None
    # Digit RUNS, not whitespace tokens. Splitting on spaces and stripping
    # ASCII punctuation left "9999؟" intact -- the Arabic question mark keeps
    # it from being a digit string, so an invented code sailed through the
    # check meant to catch it. Measured by the test below.
    for run in re.findall(r"\d+", text):
        if len(run) >= 3 and run not in codes:
            return None
    return text[:_QUESTION_LIMIT]


def validate_interpretation(
    payload: Any,
    *,
    missing_fields: Sequence[str],
    account_codes: set[str],
) -> InterpretedReply | None:
    """Everything the model said, checked before any of it is acted on.

    Modelled on ``_semantic_decision``: parse, validate against the schema,
    then check the claims the schema cannot -- that the field was one we
    asked about, that the code exists in the chart we supplied, that a value
    is one of the concepts we named. Anything unexpected returns None, which
    the caller reads as "behave as you did before".
    """
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
        # Observed alias. The contract now names the keys explicitly, so this
        # should not recur -- but a right answer under a near-miss key is
        # still a right answer, and rejecting it would have been a silent
        # regression to the deterministic re-ask.
        if isinstance(data, dict) and data.get("value") is None:
            if data.get("concept_value") is not None:
                data["value"] = data.pop("concept_value")
        interpreted = InterpretedReply.model_validate(data)
    except (TypeError, ValueError, json.JSONDecodeError, ValidationError):
        return None

    if interpreted.variant == "abandon":
        return interpreted

    if interpreted.variant == "out_of_scope":
        return interpreted

    if interpreted.variant == "unclear":
        question = _clean_question(interpreted.question, account_codes)
        if not question:
            return None
        return interpreted.model_copy(update={"question": question})

    # fill / replace -- the two that can move a draft.
    if interpreted.confidence == "low":
        # A low-confidence guess about which account money left is exactly the
        # thing RAG-19 was. Ask again instead.
        return None

    allowed = FILLABLE_FIELDS if interpreted.variant == "fill" else REPLACEABLE_FIELDS
    if interpreted.field not in allowed:
        return None
    if interpreted.variant == "fill" and interpreted.field not in set(missing_fields):
        # Filling something nobody asked about.
        return None

    if interpreted.account_code is not None:
        if str(interpreted.account_code) not in account_codes:
            # The one rule the FIXED block states and the only one that
            # matters here: codes come from the chart we sent.
            return None

    if interpreted.value is not None and interpreted.value not in CONCEPT_VALUES:
        return None

    if interpreted.account_code is None and interpreted.value is None:
        if interpreted.variant == "replace" and interpreted.amount is not None:
            return interpreted
        return None

    if interpreted.amount is not None and interpreted.amount <= 0:
        return None

    return interpreted


def interpret_clarification_reply(
    *,
    reply: str,
    missing_fields: Sequence[str],
    known_fields: Mapping[str, Any],
    question_asked: str | None,
    accounts: Sequence[Mapping[str, Any]],
    language: str,
    runtime_context: AgentRuntimeContext | None = None,
    conversation: Any | None = None,
) -> InterpretedReply | None:
    """Ask the model what the reply meant. None means "do what you did before"."""

    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not api_key or not model_calls_enabled():
        return None

    remaining = remaining_budget_seconds()
    timeout_seconds = GEMINI_REQUEST_TIMEOUT_SECONDS
    if remaining is not None:
        if remaining <= 1.0:
            # Nothing left. The deterministic answer is the one that fits.
            logger.info(
                "intent=clarification_interpreter outcome=no_budget remaining=%.1f",
                remaining,
            )
            return None
        timeout_seconds = min(timeout_seconds, remaining)

    chart = _chart_for_prompt(accounts)
    account_codes = {entry["code"] for entry in chart}

    prompt = build_agent_prompt(
        runtime_context=runtime_context
        or default_runtime_context(language=language, provider_name="gemini"),
        task_instructions=TASK_INSTRUCTIONS,
        user_message=reply,
        fixed_output_contract=FIXED_OUTPUT_CONTRACT,
        trusted_backend_data={
            "question_we_asked": question_asked,
            "fields_still_missing": list(missing_fields),
            "already_captured": dict(known_fields),
            "current_company_chart_of_accounts": chart,
        },
        untrusted_conversation=conversation or None,
    )

    try:
        from google import genai

        client = genai.Client(
            api_key=api_key,
            http_options={"timeout": int(timeout_seconds * 1000)},
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt.user_message,
            config={
                "system_instruction": prompt.system_instruction,
                "response_mime_type": "application/json",
            },
        )
        raw = (response.text or "").strip()
    except Exception as exc:
        logger.warning(
            "clarification interpreter failed safely; contract=%s provider=gemini "
            "intent=clarification_interpreter outcome=deterministic error_type=%s",
            AGENT_CONTRACT_VERSION,
            type(exc).__name__,
        )
        return None

    interpreted = validate_interpretation(
        raw, missing_fields=missing_fields, account_codes=account_codes
    )
    logger.info(
        "contract=%s provider=gemini intent=clarification_interpreter outcome=%s",
        AGENT_CONTRACT_VERSION,
        interpreted.variant if interpreted else "rejected",
    )
    return interpreted
