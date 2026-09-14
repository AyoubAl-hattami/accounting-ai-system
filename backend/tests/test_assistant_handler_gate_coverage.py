"""Every assistant handler must sit behind a role gate.

``dispatch_gemini_assistant`` runs a block of role checks and then dispatches
handlers by ``if intent == ...``.  The gates sit up to 300 lines above the
handlers they protect, so a handler appended below them receives no
authorization check and nothing fails.

That is not hypothetical.  ``pl_contribution_question`` was dispatched with no
gate and answered a role outside ``_CAN_READ_REPORTS`` with real journal
entries -- number, date, description and amount.  It is gated now; this test is
what stops the next one.

Pure AST over the source file: no HTTP, no database, no import of the module
under test.  It runs in the static CI job and fires on every pull request.

It does NOT check that each handler's gate is the *correct* one -- only that
some gate covers the intent.  Choosing the right permission set is still a
review judgement.
"""

import ast
import pathlib


SERVICE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "services" / "gemini_assistant_service.py"
)
DISPATCHER = "dispatch_gemini_assistant"

# Handlers whose gate is not a peer of the others and so cannot be detected by
# shape.  Every entry needs a reason; an empty reason is not an exemption.
INLINE_GATED_HANDLERS = {
    # Carries its own gate immediately inside the handler body:
    #     if user_role not in _CAN_READ_REPORTS: return ... access_denied
    # It is NOT moved into the main block on purpose.  The enclosing condition
    # is `intent == "structured_report_question" and structured_kind in {...}`,
    # so hoisting the role check would make it fire for values of
    # structured_kind that currently fall through to later handlers -- a
    # behaviour change, not a relocation.  Consolidating it belongs with the
    # handler-registry refactor, where the structured_kind condition can be
    # carried across deliberately.
    "structured_report_question",
}


def _dispatcher() -> ast.FunctionDef:
    tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == DISPATCHER:
            return node
    raise AssertionError(f"{DISPATCHER} not found in {SERVICE.name}")


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


def test_the_gate_block_is_still_recognisable():
    """Guard the guard: if shape detection silently matches nothing, the
    coverage assertion below would pass vacuously."""
    gated, dispatched = _gated_and_dispatched()
    assert gated, (
        "No role gates were recognised in "
        f"{DISPATCHER}. Either they were removed, or their shape changed and "
        "_is_role_gate needs updating -- do not delete this test to make it pass."
    )
    assert dispatched, f"No intent handlers were recognised in {DISPATCHER}."


def test_every_dispatched_handler_intent_is_gated():
    gated, dispatched = _gated_and_dispatched()
    ungated = dispatched - gated - INLINE_GATED_HANDLERS

    assert not ungated, (
        "These assistant handler intents are dispatched with no role gate: "
        f"{sorted(ungated)}.\n"
        "A handler added below the gate block receives no authorization check "
        "and nothing else fails. Add the intent to the matching gate in "
        f"{DISPATCHER}, or -- only if it carries its own gate inside the "
        "handler body -- add it to INLINE_GATED_HANDLERS with the reason."
    )


def test_inline_gate_allowlist_entries_still_exist_and_still_gate_themselves():
    """An exemption that no longer describes reality is worse than none."""
    gated, dispatched = _gated_and_dispatched()
    source = SERVICE.read_text(encoding="utf-8")

    for intent in INLINE_GATED_HANDLERS:
        assert intent in dispatched, (
            f"{intent!r} is exempted in INLINE_GATED_HANDLERS but is no longer "
            "dispatched. Remove the stale exemption."
        )
        assert intent not in gated, (
            f"{intent!r} is exempted as inline-gated but now also appears in the "
            "main gate block. Remove it from INLINE_GATED_HANDLERS."
        )

    # The exemption claims a role check lives inside the handler body. Verify a
    # permission-set check is present somewhere, so deleting the inline gate
    # cannot leave the exemption silently covering an ungated handler.
    assert "_CAN_READ_REPORTS" in source, (
        "The inline gate exemption assumes a permission-set check exists in "
        f"{SERVICE.name}; none was found."
    )
