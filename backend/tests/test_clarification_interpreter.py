# -*- coding: utf-8 -*-
"""Everything the interpreter is allowed to believe, and everything it is not.

These need no provider. They are the durable half of step 3's evidence: the
live table shows a model getting it right, one run at a time and subject to
quota; these show that whatever a model says, only a narrow, checked shape of
it can reach a draft.

The rule every assertion here serves: the model proposes a FIELD VALUE, and
an account is named only by a code that was in the chart we sent. Anything
else returns None, and None means the caller does what it did before this
module existed.
"""
import pytest

from app.modules.accounting.services.clarification_interpreter import (
    CONCEPT_VALUES,
    FIXED_OUTPUT_CONTRACT,
    InterpretedReply,
    validate_interpretation,
)

CODES = {"1100", "1110", "1130", "1140", "1200"}
MISSING = ["payment_source"]


def v(payload, missing=MISSING, codes=CODES):
    return validate_interpretation(payload, missing_fields=missing, account_codes=codes)


# ── what is accepted ────────────────────────────────────────────────────────


def test_a_code_from_the_chart_is_accepted():
    out = v({"variant": "fill", "field": "payment_source",
             "account_code": "1140", "confidence": "high"})
    assert out is not None
    assert out.account_code == "1140"


def test_a_concept_value_is_accepted():
    out = v({"variant": "fill", "field": "payment_source", "value": "cash"})
    assert out is not None and out.value == "cash"


def test_missing_confidence_is_not_treated_as_doubt():
    """The first live run omitted the key and returned a correct answer.

    A "low" default made that correct answer fail the confidence gate and
    fall back to the re-ask. Silence is not evidence of doubt; only an
    explicit "low" is.
    """
    out = v({"variant": "fill", "field": "payment_source", "account_code": "1140"})
    assert out is not None, "an omitted confidence must not reject a valid fill"
    assert out.confidence == "medium"


def test_the_observed_concept_value_alias_is_accepted():
    """Measured: the model answered correctly under the key `concept_value`.

    The contract now names the keys, so this should not recur -- but a right
    answer under a near-miss key is still a right answer.
    """
    out = v({"variant": "fill", "field": "payment_source", "concept_value": "cash"})
    assert out is not None and out.value == "cash"


def test_abandon_and_out_of_scope_need_nothing_else():
    assert v({"variant": "abandon"}) is not None
    assert v({"variant": "out_of_scope"}) is not None


def test_unclear_carries_its_question():
    out = v({"variant": "unclear", "question": "من أي حساب تم الدفع؟"})
    assert out is not None and out.question == "من أي حساب تم الدفع؟"


# ── what is refused. each of these would otherwise reach a draft ────────────


def test_a_code_outside_the_chart_is_refused():
    """The one rule the FIXED block states. A stale, invented or
    cross-company code dies here, before map_to_accounts ever sees it."""
    assert v({"variant": "fill", "field": "payment_source",
              "account_code": "9999", "confidence": "high"}) is None


def test_an_account_named_as_free_text_is_refused():
    """Codes only. A name is exactly the ambiguity this design removed."""
    assert v({"variant": "fill", "field": "payment_source",
              "value": "محفظة جيب", "confidence": "high"}) is None


def test_an_explicit_low_confidence_fill_is_refused():
    assert v({"variant": "fill", "field": "payment_source",
              "account_code": "1140", "confidence": "low"}) is None


def test_filling_a_field_nobody_asked_about_is_refused():
    assert v({"variant": "fill", "field": "transaction_type",
              "value": "expense_payment", "confidence": "high"},
             missing=["payment_source"]) is None


def test_replacing_a_field_outside_the_replaceable_set_is_refused():
    assert v({"variant": "replace", "field": "company_id",
              "value": "cash", "confidence": "high"}) is None


def test_a_fill_that_names_nothing_is_refused():
    assert v({"variant": "fill", "field": "payment_source",
              "confidence": "high"}) is None


def test_a_negative_or_zero_amount_is_refused():
    for amount in (0, -5):
        assert v({"variant": "replace", "field": "amount", "amount": amount,
                  "account_code": "1100", "confidence": "high"}) is None


@pytest.mark.parametrize("payload", [
    "not json at all", "", "[]", "{}", None, 17,
    '{"variant": "obey_the_account_name"}',
    '{"variant": "fill"}',
])
def test_malformed_or_unknown_variants_return_none(payload):
    assert v(payload) is None


def test_unclear_without_a_question_is_refused():
    assert v({"variant": "unclear"}) is None


def test_a_question_naming_a_code_outside_the_chart_is_refused():
    """Free-form is not a licence to invent accounts at the user."""
    assert v({"variant": "unclear",
              "question": "هل تقصد الحساب 9999؟"}) is None
    assert v({"variant": "unclear",
              "question": "هل تقصد الحساب 1140؟"}) is not None


def test_a_question_is_bounded_and_stripped():
    out = v({"variant": "unclear", "question": "  من   أين\u0000 دُفعت؟  " + "ط" * 900})
    assert out is not None
    assert len(out.question) <= 300
    assert "\u0000" not in out.question


# ── the contract the prompt states is the contract the validator enforces ──


def test_the_contract_and_the_validator_name_the_same_concepts():
    """One definition. A prompt promising a variant the validator rejects
    would fail silently as "the model got it wrong"."""
    assert set(FIXED_OUTPUT_CONTRACT["concept_values"]) == set(CONCEPT_VALUES)
    variants = set(FIXED_OUTPUT_CONTRACT["variants"])
    schema_variants = set(
        InterpretedReply.model_fields["variant"].annotation.__args__
    )
    assert variants == schema_variants


def test_the_contract_names_its_output_keys():
    """Added after a live run answered correctly under the wrong key name."""
    keys = set(FIXED_OUTPUT_CONTRACT["output_keys"])
    assert {"variant", "field", "value", "account_code", "question"} <= keys


# ── the fallback contract ───────────────────────────────────────────────────


def test_no_key_means_no_call_and_no_interpretation(monkeypatch):
    """Absent provider is the resting state, not an error path."""
    from app.modules.accounting.services import clarification_interpreter as module

    monkeypatch.setattr(module.settings, "GEMINI_API_KEY", "")
    called = []
    monkeypatch.setattr(module, "build_agent_prompt",
                        lambda **k: called.append(1))
    out = module.interpret_clarification_reply(
        reply="من محفظة جيب", missing_fields=MISSING, known_fields={},
        question_asked="?", accounts=[], language="ar",
    )
    assert out is None
    assert not called, "a prompt was built with no key configured"


def test_a_spent_budget_makes_no_call(monkeypatch):
    from app.modules.accounting.services import clarification_interpreter as module

    monkeypatch.setattr(module.settings, "GEMINI_API_KEY", "key")
    monkeypatch.setattr(module, "remaining_budget_seconds", lambda: 0.2)
    called = []
    monkeypatch.setattr(module, "build_agent_prompt", lambda **k: called.append(1))
    out = module.interpret_clarification_reply(
        reply="من محفظة جيب", missing_fields=MISSING, known_fields={},
        question_asked="?", accounts=[], language="ar",
    )
    assert out is None
    assert not called, "a call was made with no budget left"
