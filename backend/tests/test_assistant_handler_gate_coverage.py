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

THE SECOND DISPATCH PATH
------------------------
``dispatch_unified_agent`` answers the same endpoint by letting Gemini call
tools from ``AccountingToolRegistry`` instead of resolving an intent, so none of
the invariants above can see it. It arrived with its own copy of the ``_CAN_*``
sets, already two roles wider than the originals, and a viewer could read every
member's email through it while REST answered the same viewer with 403. The
last three tests in this file close that: the tool registry must IMPORT the
permission vocabulary rather than restate it, every tool must carry one of those
sets, and no tool may be reachable by a role its REST equivalent refuses.

The tool registry is read as source, not imported: it pulls in google.genai,
sqlalchemy and settings, which would make this file need the stack and drop it
out of the static job.

It still does NOT check that an INTENT handler's gate is the correct one.
Choosing the right permission set there remains a review judgement; for tools,
the REST comparison below decides it.
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
#
# Empty now. structured_report_question was the only entry, and its gate is a
# field of its registry entry rather than a statement inside its body, so
# there is nothing left to exempt. The allowlist test below still runs and
# now asserts over an empty set, which is what it should assert.
INLINE_GATED_HANDLERS: set[str] = set()

# Produced by the resolution chain but deliberately not dispatched by any
# handler.  Each needs a reason.
#
# Empty. "unknown" was the last entry and is now registered like every other
# intent: it is what the classifier returns when nothing matched, and what
# answers it is the tool-calling model with the capability menu behind it.
# Being registered is what puts it behind a permission set and inside the
# invariants below.
NOT_DISPATCHED: set[str] = set()


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


# ── the tool-calling path: AccountingToolRegistry ────────────────────────────

TOOL_REGISTRY = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "services" / "accounting_tool_registry.py"
)
ROUTES = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "routes"
)
COMPANY_USER_MODEL = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "models" / "company_user.py"
)
PERMISSION_SOURCE = "assistant_handler_registry"

# What each tool's data is behind over REST, as (route module, endpoint).
#
# Every tool needs an entry: an unlisted tool fails the first test below, which
# is the point -- adding a tool is choosing who may call it, and that choice is
# best made against the route that already answers the same question.
#
# A tool whose REST endpoint takes no allowed_roles is readable by every member
# there, so the comparison passes for any set. It is still listed, so the claim
# is checked rather than assumed.
TOOL_REST_EQUIVALENT = {
    "get_profit_loss": ("report_routes.py", "profit_and_loss_endpoint"),
    "get_balance_sheet": ("report_routes.py", "balance_sheet_endpoint"),
    "get_trial_balance": ("report_routes.py", "trial_balance_endpoint"),
    "get_account_ledger": ("report_routes.py", "account_ledger_endpoint"),
    "get_general_ledger": ("report_routes.py", "general_ledger_endpoint"),
    "get_accounts": ("account_routes.py", "list_accounts_endpoint"),
    "get_journal_entries": ("journal_routes.py", "list_journal_entries_endpoint"),
    "trace_amount": ("journal_routes.py", "list_journal_entries_endpoint"),
    "get_audit_logs": ("audit_routes.py", "list_audit_logs_endpoint"),
    "get_company_users": ("company_user_routes.py", "list_company_users_endpoint"),
    "get_invoices": ("invoice_routes.py", "list_invoices_endpoint"),
    "get_invoice_details": ("invoice_routes.py", "get_invoice_endpoint"),
    "get_payments": ("payment_routes.py", "list_payments_endpoint"),
    "get_ar_aging": ("report_routes.py", "ar_aging_endpoint"),
    "get_ap_aging": ("report_routes.py", "ap_aging_endpoint"),
    "get_customer_statement": ("partner_routes.py", "partner_statement_endpoint"),
    "get_vendor_statement": ("partner_routes.py", "partner_statement_endpoint"),
    "get_credit_notes": ("credit_note_routes.py", "list_credit_notes_endpoint"),
    "get_credit_note_details": ("credit_note_routes.py", "get_credit_note_endpoint"),
    "get_refunds": ("refund_routes.py", "list_refunds_endpoint"),
    # The proposal tool mutates nothing: it returns a draft the user has to
    # confirm, and /confirm-action re-validates it. Compared against the create
    # route anyway, because proposing an entry only an accountant may create is
    # an invitation to a 403 one step later.
    "propose_journal_entry": ("journal_routes.py", "create_journal_entry_endpoint"),
}


def _tool_registry_module() -> ast.Module:
    return ast.parse(TOOL_REGISTRY.read_text(encoding="utf-8"))


def _tool_permission_names() -> dict[str, str]:
    """tool name -> the name of the permission set its _HANDLERS entry carries."""
    found: dict[str, str] = {}
    for node in ast.walk(_tool_registry_module()):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not (isinstance(node.target, ast.Name) and node.target.id == "_HANDLERS"):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                continue
            if not (isinstance(value, ast.Tuple) and len(value.elts) >= 2):
                continue
            permission = value.elts[1]
            found[key.value] = (
                permission.id
                if isinstance(permission, ast.Name)
                else ast.dump(permission)
            )
    return found


def _role_vocabulary() -> frozenset[str]:
    """Every role a company_users row may hold, from the model's check constraint."""
    for node in ast.walk(ast.parse(COMPANY_USER_MODEL.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("role IN ("):
                inner = node.value[len("role IN ("):].rstrip(")")
                return frozenset(part.strip().strip("'\"") for part in inner.split(","))
    raise AssertionError(f"No role check constraint found in {COMPANY_USER_MODEL.name}")


def _rest_roles(module_name: str, function_name: str) -> frozenset[str] | None:
    """Roles the endpoint admits, or None when it admits every member.

    Roles outside the vocabulary are dropped: the invoice, payment and partner
    reads list a role named "user", which no row can hold, so it admits nobody.
    """
    path = ROUTES / module_name
    assert path.exists(), f"{module_name} not found in {ROUTES}"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.FunctionDef) and node.name == function_name):
            continue
        for keyword in ast.walk(node):
            if not isinstance(keyword, ast.keyword) or keyword.arg != "allowed_roles":
                continue
            if isinstance(keyword.value, (ast.Set, ast.List, ast.Tuple)):
                named = frozenset(
                    element.value
                    for element in keyword.value.elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                )
                return named & _role_vocabulary()
        return None
    raise AssertionError(f"{function_name} not found in {module_name}")


def test_tool_registry_is_still_detectable():
    """Same guard-the-guard reasoning as above: a renamed _HANDLERS or a
    restructured entry must fail loudly, not pass vacuously."""
    assert _tool_permission_names(), (
        f"No tool entries were found in {TOOL_REGISTRY.name}. _HANDLERS was "
        "renamed or changed shape and the parser above needs updating -- do "
        "not delete this test to make it pass."
    )
    assert _role_vocabulary(), "No role vocabulary was parsed from the model."


def test_tool_registry_imports_the_permission_vocabulary_and_defines_none():
    """The bypass this catches is a LOCAL _CAN_* set.

    A local set does not fail the membership test below by itself: someone
    reintroducing ``_CAN_READ_USERS = frozenset({"admin", "viewer"})`` at the
    top of the tool registry would shadow the import, and every other assertion
    here would still pass -- the name still resolves and the tools still carry
    "a" set. The only thing that separates the two is where the name is bound,
    so that is what this asserts.
    """
    module = _tool_registry_module()

    local = {
        target.id
        for node in ast.walk(module)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.startswith("_CAN_")
    } | {
        node.target.id
        for node in ast.walk(module)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id.startswith("_CAN_")
    }
    assert not local, (
        f"{TOOL_REGISTRY.name} defines its own permission set(s): {sorted(local)}.\n"
        "It had four once, all wider than the originals, and a viewer read "
        "every member's email through the assistant while REST refused the "
        f"same viewer. Import them from {PERMISSION_SOURCE} instead."
    )

    imported = {
        alias.name
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.endswith(PERMISSION_SOURCE)
        for alias in node.names
        if alias.name.startswith("_CAN_")
    }
    missing = set(_tool_permission_names().values()) - imported
    assert not missing, (
        "These permission names gate tools but are not imported from "
        f"{PERMISSION_SOURCE}: {sorted(missing)}. Wherever they come from, it "
        "is not the one definition."
    )


def _declared_tool_names() -> set[str]:
    """Tool names in TOOL_DECLARATIONS, which is what the model is offered."""
    found: set[str] = set()
    for node in ast.walk(_tool_registry_module()):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "TOOL_DECLARATIONS"
            for target in node.targets
        ):
            continue
        for element in getattr(node.value, "elts", []):
            for keyword in getattr(element, "keywords", []):
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    found.add(keyword.value.value)
    return found


def test_what_is_offered_and_what_is_handled_are_the_same_set():
    """A declaration with no handler is a tool the model can call and the
    registry then refuses as unknown; a handler with no declaration is a gate
    nothing reaches. Removing a tool means removing both, and the two lists
    are 300 lines apart."""
    declared = _declared_tool_names()
    handled = set(_tool_permission_names())
    assert declared, "No FunctionDeclaration names were parsed; the shape changed."
    assert declared == handled, (
        f"offered but not handled: {sorted(declared - handled)}; "
        f"handled but not offered: {sorted(handled - declared)}"
    )


def test_every_tool_carries_a_known_permission_set():
    known = _permission_sets()
    for tool, permission_name in sorted(_tool_permission_names().items()):
        assert permission_name in known, (
            f"Tool {tool!r} is gated by {permission_name!r}, which is not one "
            f"of the _CAN_* sets in {PERMISSION_SOURCE}: {sorted(known)}."
        )
        assert known[permission_name], (
            f"Tool {tool!r} is gated by {permission_name!r}, which is empty: "
            "it would authorise nobody and gate nothing."
        )


def test_no_tool_is_withheld_from_a_role_rest_admits():
    """The other direction, and the one [RAG-9] was.

    The tool registry's own _CAN_READ_REPORTS omitted reviewer and approver,
    so those two roles were offered ZERO tools while REST answered their
    report requests with 200. A gate that is too narrow is not a safe
    mistake -- it is a role that cannot use the product, and it hid behind
    "the assistant is optional" for as long as nobody measured it.

    Only endpoints that take no allowed_roles are checked: those admit every
    member, so the tool behind them must too.
    """
    permission_sets = _permission_sets()
    vocabulary = _role_vocabulary()

    for tool, permission_name in sorted(_tool_permission_names().items()):
        module_name, function_name = TOOL_REST_EQUIVALENT[tool]
        if _rest_roles(module_name, function_name) is not None:
            continue
        missing = vocabulary - permission_sets[permission_name]
        assert not missing, (
            f"Tool {tool!r} is withheld from {sorted(missing)}, whom "
            f"{module_name}:{function_name} admits -- it takes no "
            "allowed_roles, so every member of the company may read it there."
        )


def test_no_tool_is_reachable_by_a_role_rest_would_refuse():
    """The assistant is a second door onto the same data, not a wider one."""
    permission_sets = _permission_sets()
    tools = _tool_permission_names()

    unlisted = set(tools) - set(TOOL_REST_EQUIVALENT)
    assert not unlisted, (
        f"These tools have no REST equivalent recorded: {sorted(unlisted)}.\n"
        "Add each to TOOL_REST_EQUIVALENT naming the route that answers the "
        "same question, so its role set is checked against that route's."
    )

    stale = set(TOOL_REST_EQUIVALENT) - set(tools)
    assert not stale, (
        f"TOOL_REST_EQUIVALENT names tools that no longer exist: {sorted(stale)}."
    )

    for tool, permission_name in sorted(tools.items()):
        module_name, function_name = TOOL_REST_EQUIVALENT[tool]
        rest = _rest_roles(module_name, function_name)
        if rest is None:
            continue
        allowed = permission_sets[permission_name]
        wider = allowed - rest
        assert not wider, (
            f"Tool {tool!r} is callable by {sorted(wider)}, whom "
            f"{module_name}:{function_name} answers with 403.\n"
            f"Tool gate {permission_name} = {sorted(allowed)}; REST allows "
            f"{sorted(rest)}. Either narrow the tool's set or change the "
            "route -- but the assistant must not be the wider door."
        )
