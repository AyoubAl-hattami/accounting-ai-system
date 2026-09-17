"""Every assistant handler must sit behind a role gate -- inline or registered.

``dispatch_gemini_assistant`` resolves an intent and then answers it. Handlers
are being moved out of its ``if intent == ...`` chain and into
``ASSISTANT_HANDLERS``, where each entry binds its handler to the permission set
that authorises it. During that migration both forms exist at once, so this file
holds one invariant that is true before it starts, after it finishes, and at
every commit in between:

    every intent the resolution chain can produce is dispatched at most once,
    inline or from the registry, and whichever way it is dispatched, it is gated.

WHY THIS FILE WAS REWRITTEN
---------------------------
The previous version detected dispatch by SHAPE: it walked ``ast.If`` nodes
inside one function looking for ``intent == "..."``. That is the right test for
an if-chain and the wrong one for a registry -- the moment handlers move out, it
finds nothing, and its own guard-the-guard assertion fails. It was designed to
fail loudly rather than pass vacuously, and it did its job; this is its
successor, not its deletion.

The threat model changed with it. Before: a handler appended below the gate
block gets no gate. Now: a handler dispatched inline, bypassing the registry and
therefore the gate. Both are covered below.

One hole the old version did not cover is closed here: an intent that the
resolution chain can produce but that nothing dispatches. That used to fall
through silently.

Pure AST plus one import of the registry module, which is dataclasses only --
it pulls in neither the service, nor sqlalchemy, nor settings (measured: 0.06s,
no side effects). No HTTP, no database. It runs in the static CI job.

It still does NOT check that a handler's gate is the CORRECT one. Choosing the
right permission set remains a review judgement.
"""

import ast
import pathlib

from app.modules.accounting.services import assistant_handler_registry
from app.modules.accounting.services.assistant_handler_registry import (
    ASSISTANT_HANDLERS,
)

SERVICE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "services" / "gemini_assistant_service.py"
)
DISPATCHER = "dispatch_gemini_assistant"
CLASSIFIER = "_classify_intent"

# Handlers whose gate is not a peer of the others and so cannot be detected by
# shape.  Every entry needs a reason; an empty reason is not an exemption.
# This set empties itself as the migration proceeds: a registered handler
# carries its gate in a field, so there is nothing left to exempt.
INLINE_GATED_HANDLERS = {
    # Carries its own gate immediately inside the handler body:
    #     if user_role not in _CAN_READ_REPORTS: return ... access_denied
    # The enclosing condition is `intent == "structured_report_question" and
    # structured_kind in {...}`.  When this handler is registered, that
    # condition becomes its `precondition` field and the gate becomes its
    # `permission` field, and this exemption goes away.
    "structured_report_question",
}

# Produced by the resolution chain but deliberately not dispatched by any
# handler.  Each needs a reason.
NOT_DISPATCHED = {
    # Falls past the whole chain to the clarification reply at the end of the
    # dispatcher.  It is what the classifier returns when nothing matched, so
    # there is nothing to authorise.
    "unknown",
}


def _module() -> ast.Module:
    return ast.parse(SERVICE.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
    for node in ast.walk(_module()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {SERVICE.name}")


def _dispatcher() -> ast.FunctionDef:
    return _function(DISPATCHER)


def _intents_compared(test: ast.AST) -> set[str]:
    """Literal values this condition asserts `intent` to BE.

    Only `==` and `in` count.  `intent not in (...)` appears in the
    normalisation code above the gates and says nothing about what a branch
    handles.
    """
    found: set[str] = set()
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "intent"):
            continue
        if not all(isinstance(op, (ast.Eq, ast.In)) for op in node.ops):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                found.add(comparator.value)
            elif isinstance(comparator, (ast.Tuple, ast.List, ast.Set)):
                found |= {
                    element.value
                    for element in comparator.elts
                    if isinstance(element, ast.Constant) and isinstance(element.value, str)
                }
    return found


def _is_role_gate(node: ast.If) -> bool:
    """A gate tests a role against a permission set and refuses.

    Identified by shape rather than by line number, so the test keeps working
    as the 3,900-line file moves around it.
    """
    mentions_permission_set = any(
        isinstance(inner, ast.Name) and inner.id.startswith("_CAN_")
        for inner in ast.walk(node.test)
    )
    if not mentions_permission_set:
        return False
    return any(
        isinstance(keyword, ast.keyword)
        and keyword.arg == "intent"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == "access_denied"
        for statement in node.body
        for keyword in ast.walk(statement)
        if isinstance(keyword, ast.keyword)
    )


def _answers_the_user(node: ast.If) -> bool:
    """A handler returns a reply; the branches above the gates only reassign.

    `if intent == "unknown" and looks_like_accounting_message_with_amount(...)`
    rewrites `intent` and falls through -- it dispatches nothing, so it is not
    something a gate could protect.
    """
    return any(isinstance(inner, ast.Return) for inner in ast.walk(node))


def _gated_and_dispatched() -> tuple[set[str], set[str]]:
    """What the INLINE if-chain still gates, and what it still dispatches."""
    gated: set[str] = set()
    dispatched: set[str] = set()
    for node in ast.walk(_dispatcher()):
        if not isinstance(node, ast.If):
            continue
        intents = _intents_compared(node.test)
        if not intents:
            continue
        if _is_role_gate(node):
            gated |= intents
        elif _answers_the_user(node):
            dispatched |= intents
    return gated, dispatched


def _registered_intents() -> set[str]:
    intents: set[str] = set()
    for entry in ASSISTANT_HANDLERS:
        intents |= set(entry.intents)
    return intents


def _producible_intents() -> set[str]:
    """Every value the resolution chain can leave in `intent`.

    Three sources, matching the override chain: what `_classify_intent` returns,
    what `handler_to_legacy_intent` maps an orchestrator handler to, and what the
    dispatcher assigns to `intent` directly.
    """
    found: set[str] = set()

    for node in ast.walk(_function(CLASSIFIER)):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                found.add(node.value.value)

    dispatcher = _dispatcher()
    for node in ast.walk(dispatcher):
        if not isinstance(node, ast.Assign):
            continue
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "intent" in targets:
            # Covers the plain assignment and the conditional expression at 3608.
            found |= {
                inner.value
                for inner in ast.walk(node.value)
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
            }
        if "handler_to_legacy_intent" in targets and isinstance(node.value, ast.Dict):
            found |= {
                value.value
                for value in node.value.values
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            }
    return found


def _permission_sets() -> dict[str, frozenset[str]]:
    """The `_CAN_*` role sets.

    They live in the registry module, not the service: a registry entry has to
    name the set that gates it, and the service imports the registry, so the
    service cannot own them without a cycle. The service imports them back under
    the same names, which is why the AST gate detection above still works.

    Read as objects rather than parsed out of source, so this compares against
    the one definition rather than a transcription of it.
    """
    return {
        name: value
        for name, value in vars(assistant_handler_registry).items()
        if name.startswith("_CAN_") and isinstance(value, frozenset)
    }


# ── guard the guard ──────────────────────────────────────────────────────────


def test_dispatch_is_still_detectable_in_at_least_one_form():
    """If every detector silently matched nothing, the assertions below would
    all pass vacuously -- which is exactly how the gap this file exists to catch
    would reappear."""
    _, inline = _gated_and_dispatched()
    assert inline or ASSISTANT_HANDLERS, (
        "No handler was found inline OR in the registry. Either dispatch moved "
        "somewhere this file does not look, or its shape changed and the "
        "detectors need updating -- do not delete these tests to make them pass."
    )
    assert _producible_intents(), (
        "No producible intents were found. The resolution chain moved or "
        "changed shape; _producible_intents needs updating."
    )
    assert _permission_sets(), (
        "No _CAN_* permission sets were found in assistant_handler_registry."
    )


# ── the invariant, true at every point of the migration ──────────────────────


def test_every_inline_dispatched_handler_intent_is_gated():
    gated, inline = _gated_and_dispatched()
    ungated = inline - gated - INLINE_GATED_HANDLERS

    assert not ungated, (
        "These assistant handler intents are dispatched inline with no role "
        f"gate: {sorted(ungated)}.\n"
        "A handler added below the gate block receives no authorization check "
        "and nothing else fails. Add the intent to the matching gate in "
        f"{DISPATCHER}, register it in ASSISTANT_HANDLERS where the gate is a "
        "field, or -- only if it carries its own gate inside the handler body "
        "-- add it to INLINE_GATED_HANDLERS with the reason."
    )


def test_every_registered_handler_carries_a_real_permission():
    known = set(_permission_sets().values())
    for entry in ASSISTANT_HANDLERS:
        assert entry.permission, (
            f"Registered handler for {sorted(entry.intents)} has an empty "
            "permission set, which would authorise nobody and gate nothing. "
            "Give it the _CAN_* set that guards it."
        )
        assert entry.permission in known, (
            f"Registered handler for {sorted(entry.intents)} carries a "
            f"permission set that is not one of the _CAN_* sets: "
            f"{sorted(entry.permission)}. A bespoke role set "
            "here is how two places drift apart about who may read what."
        )


def test_no_intent_is_dispatched_both_inline_and_from_the_registry():
    _, inline = _gated_and_dispatched()
    both = inline & _registered_intents()

    assert not both, (
        f"These intents are dispatched twice: {sorted(both)}.\n"
        "The registry loop runs before the remaining if-chain, so the inline "
        "branch is now dead code that still looks live. Delete the inline "
        "branch in the same commit that registers the handler."
    )


def test_every_producible_intent_is_dispatched_somewhere():
    _, inline = _gated_and_dispatched()
    undispatched = _producible_intents() - inline - _registered_intents() - NOT_DISPATCHED

    assert not undispatched, (
        f"The resolution chain can produce these intents and nothing answers "
        f"them: {sorted(undispatched)}.\n"
        "They fall through to the generic clarification reply, which looks like "
        "the assistant not understanding rather than a missing handler. Add a "
        "handler, or add the intent to NOT_DISPATCHED with the reason."
    )


def test_registered_intents_are_unique():
    seen: set[str] = set()
    for entry in ASSISTANT_HANDLERS:
        for intent in entry.intents:
            assert intent not in seen, (
                f"{intent!r} is registered by more than one handler entry. The "
                "loop returns on first match, so the later entry is unreachable."
            )
            seen.add(intent)


def test_inline_gate_allowlist_entries_still_exist_and_still_gate_themselves():
    """An exemption that no longer describes reality is worse than none."""
    gated, inline = _gated_and_dispatched()
    registered = _registered_intents()
    source = SERVICE.read_text(encoding="utf-8")

    for intent in INLINE_GATED_HANDLERS:
        assert intent in inline, (
            f"{intent!r} is exempted in INLINE_GATED_HANDLERS but is no longer "
            "dispatched inline. If it moved into the registry its gate is now a "
            "field -- remove the stale exemption."
        )
        assert intent not in gated, (
            f"{intent!r} is exempted as inline-gated but now also appears in the "
            "main gate block. Remove it from INLINE_GATED_HANDLERS."
        )
        assert intent not in registered, (
            f"{intent!r} is exempted as inline-gated and is also registered. "
            "Remove the exemption."
        )

    # The exemption claims a role check lives inside the handler body. Verify a
    # permission-set check is present somewhere, so deleting the inline gate
    # cannot leave the exemption silently covering an ungated handler.
    assert "_CAN_READ_REPORTS" in source, (
        "The inline gate exemption assumes a permission-set check exists in "
        f"{SERVICE.name}; none was found."
    )
