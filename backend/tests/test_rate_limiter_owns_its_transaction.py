"""The rate limiter must not write through the request's session.

The login endpoint records a failed attempt and then raises 401.  ``get_db``
only closes the request session -- no rollback, no commit -- and closing a
session with an open transaction discards it.  A failed login's audit row
survives solely because ``create_audit_log(commit=True)`` runs immediately
after ``record_attempt`` and sweeps both into one commit.

So a limiter that wrote through that session would be durable by accident of
call ordering.  Move the audit call, drop its commit, or add an early return,
and the recorded attempt disappears -- and a disappeared attempt is a free
retry, which is the whole control.

This file exists so that reintroducing the coupling fails the suite.  Pure AST
over app/core/rate_limit.py: no HTTP, no database, no import of the module under
test, so it runs in the static CI job on every pull request.

It does NOT check that the limiter is correct, only that it owns its
transaction.  Whether the counting is right is measured against a live stack.
"""

import ast
import pathlib


LIMITER = (
    pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "rate_limit.py"
)

# The functions that read or write limiter state. Each must be self-contained.
STATEFUL_FUNCTIONS = frozenset({"is_rate_limited", "record_attempt", "reset_attempts"})

# A parameter by any of these names would mean a caller handing in its session.
SESSION_PARAMETER_NAMES = frozenset({"db", "session", "conn", "connection"})


def _module() -> ast.Module:
    return ast.parse(LIMITER.read_text(encoding="utf-8"))


def _functions() -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in ast.walk(_module())
        if isinstance(node, ast.FunctionDef)
    }


def test_the_stateful_functions_still_exist():
    """Guard the guard: if these were renamed, every assertion below would pass
    vacuously."""
    found = set(_functions()) & STATEFUL_FUNCTIONS
    assert found == STATEFUL_FUNCTIONS, (
        f"Expected {sorted(STATEFUL_FUNCTIONS)} in {LIMITER.name}, found "
        f"{sorted(found)}. If they were renamed, update this file rather than "
        "deleting it."
    )


def test_no_stateful_function_accepts_a_session_from_its_caller():
    functions = _functions()
    offenders = []
    for name in sorted(STATEFUL_FUNCTIONS):
        node = functions[name]
        arguments = node.args
        parameters = [
            argument.arg
            for argument in (
                arguments.posonlyargs + arguments.args + arguments.kwonlyargs
            )
        ]
        taken = sorted(set(parameters) & SESSION_PARAMETER_NAMES)
        if taken:
            offenders.append(f"  {name}() takes {taken}")

    assert not offenders, (
        "The rate limiter must not write through a session it was handed:\n"
        + "\n".join(offenders)
        + "\nThe request session is discarded when the 401 is raised, so an "
        "attempt recorded in it is only durable if some later call happens to "
        "commit. Open a session here and commit it before returning."
    )


def test_each_stateful_function_opens_and_commits_its_own_session():
    functions = _functions()
    missing = []
    for name in sorted(STATEFUL_FUNCTIONS):
        node = functions[name]
        calls = [
            inner.func.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
        ]
        methods = [
            inner.func.attr
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
        ]
        if "SessionLocal" not in calls:
            missing.append(f"  {name}() never calls SessionLocal()")
        # A reader has nothing to commit; only the writers must.
        elif name != "is_rate_limited" and "commit" not in methods:
            missing.append(f"  {name}() opens a session but never commits it")

    assert not missing, (
        "Every stateful limiter function must own its transaction:\n"
        + "\n".join(missing)
    )
