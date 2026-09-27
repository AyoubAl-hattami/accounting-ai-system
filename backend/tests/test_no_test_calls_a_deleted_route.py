"""No test may call an endpoint the application no longer serves.

``POST /company-users`` was removed because it let a company admin enumerate
every account on the platform.  The commit that removed it migrated the nine
call sites it found and added a route-table assertion so the route could not
come back.  It missed a tenth call site in test_invitation_lifecycle_integrity
-- a file the offline suite cannot run -- and that test went on failing against
a live server for as long as nobody had a live server.

A guard that says "the route is gone" cannot see a caller that still wants it.
This one reads from the other end: it collects every HTTP call the test tree
makes and asserts each one names a route the application actually registers.

Pure AST plus the in-process route table: no requests, no database, no server.
It runs in the static CI job and fires on every pull request, which is the only
way a deleted route's orphaned callers get noticed before an integration run.

What it does NOT check: that the request body, query string or auth are right.
Only that something is listening at that method and path.
"""

import ast
import pathlib

from app.main import app


TESTS_DIR = pathlib.Path(__file__).resolve().parent
HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options"}

# A hole in an f-string: a replacement field whose value is not known statically.
HOLE = "\x00"

# Call sites whose URL this module cannot resolve by shape.  Every entry needs a
# reason.  A test below asserts the list still describes reality, so an entry
# cannot outlive the code it excuses.
UNRESOLVABLE_CALL_SITES: dict[tuple[str, int], str] = {}

# Call sites that name a route the application does not serve.  Empty, and
# meant to stay that way: it existed to let this guard ship green over two
# pre-existing orphans in test_protected_company_users, and emptied itself when
# those were repointed at the real endpoints -- the staleness test below failed
# the moment they resolved, which is what it is for.  An entry here is a defect
# being deferred, not an exemption earned.
KNOWN_ORPHANED_CALL_SITES: dict[tuple[str, int], str] = {}


def _template(node: ast.AST) -> str | None:
    """The literal shape of a string expression, with holes for interpolation."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
            else HOLE
            for part in node.values
        )
    return None


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level ``NAME = "/literal"`` bindings, where endpoints are often held."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = _template(node.value)
            if isinstance(target, ast.Name) and value is not None and HOLE not in value:
                constants[target.id] = value
    return constants


def _with_constants(
    node: ast.AST,
    constants: dict[str, str],
    builders: dict[str, str] | None = None,
) -> str | None:
    """Like ``_template``, but filling holes whose value is known statically.

    Two kinds are filled: a module constant, and a call to a module-local URL
    builder.  ``f"{_platform_url(base_url)}/{company.id}"`` is the common shape,
    and resolves to the builder's own template followed by ``/`` and a hole.
    """
    builders = builders or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.JoinedStr):
        return None
    parts = []
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            parts.append(part.value)
            continue
        if isinstance(part, ast.FormattedValue):
            inner = part.value
            if isinstance(inner, ast.Name) and inner.id in constants:
                parts.append(constants[inner.id])
                continue
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id in builders
            ):
                parts.append(builders[inner.func.id])
                continue
        parts.append(HOLE)
    return "".join(parts)


def _url_builders(tree: ast.Module, constants: dict[str, str]) -> dict[str, str]:
    """Module-local helpers of the form ``def _url(base): return f"{base}/x"``."""
    builders: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or len(node.body) != 1:
            continue
        statement = node.body[0]
        if not isinstance(statement, ast.Return) or statement.value is None:
            continue
        template = _with_constants(statement.value, constants)
        if template is not None and template.startswith(HOLE):
            builders[node.name] = template
    return builders


def _request_wrappers(tree: ast.Module) -> dict[str, tuple[int, int]]:
    """Module-local wrappers around ``requests.request(method, f"{base}{path}")``.

    Returns the positional index of the method argument and of the path
    argument, so a call to the wrapper resolves from its own arguments.  Without
    this, one wrapper would hide every endpoint its file touches behind a single
    unreadable call.
    """
    wrappers: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        names = [argument.arg for argument in node.args.args]
        for inner in ast.walk(node):
            if not (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "request"
                and isinstance(inner.func.value, ast.Name)
                and inner.func.value.id == "requests"
                and len(inner.args) >= 2
            ):
                continue
            method_arg, url_arg = inner.args[0], inner.args[1]
            if not (isinstance(method_arg, ast.Name) and isinstance(url_arg, ast.JoinedStr)):
                continue
            interpolated = [
                value.value.id
                for value in url_arg.values
                if isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name)
            ]
            if len(interpolated) != 2 or method_arg.id not in names:
                continue
            base_name, path_name = interpolated
            if base_name in names and path_name in names:
                wrappers[node.name] = (names.index(method_arg.id), names.index(path_name))
    return wrappers


def _call_sites() -> tuple[list[tuple[str, int, str, str]], list[tuple[str, int, str]]]:
    """Every HTTP call the test tree makes: (file, line, METHOD, url template)."""
    resolved: list[tuple[str, int, str, str]] = []
    unresolved: list[tuple[str, int, str]] = []

    for path in sorted(TESTS_DIR.rglob("*.py")):
        # utf-8-sig: at least one test file carries a byte-order mark.
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        constants = _module_constants(tree)
        builders = _url_builders(tree, constants)
        wrappers = _request_wrappers(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func

            # requests.<verb>(url, ...)
            if (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id == "requests"
                and function.attr in HTTP_VERBS
            ):
                if not node.args:
                    unresolved.append((path.name, node.lineno, "no positional url"))
                    continue
                argument = node.args[0]
                template = _with_constants(argument, constants, builders)
                if template is None and isinstance(argument, ast.Call):
                    called = argument.func
                    if isinstance(called, ast.Name) and called.id in builders:
                        template = builders[called.id]
                if template is None:
                    unresolved.append((path.name, node.lineno, type(argument).__name__))
                else:
                    resolved.append((path.name, node.lineno, function.attr.upper(), template))
                continue

            # wrapper("POST", base_url, "/path", ...)
            if isinstance(function, ast.Name) and function.id in wrappers:
                method_index, path_index = wrappers[function.id]
                if len(node.args) <= max(method_index, path_index):
                    unresolved.append(
                        (path.name, node.lineno, f"{function.id} given too few positional args")
                    )
                    continue
                method_template = _with_constants(node.args[method_index], constants, builders)
                path_template = _with_constants(node.args[path_index], constants, builders)
                if method_template is None or path_template is None:
                    unresolved.append(
                        (path.name, node.lineno, f"{function.id} arguments are not literal")
                    )
                else:
                    resolved.append(
                        (path.name, node.lineno, method_template.upper(), HOLE + path_template)
                    )

    return resolved, unresolved


def _segments(path: str) -> list[str]:
    """Path segments, with every dynamic one collapsed to ``*``.

    A segment is dynamic if it holds an f-string hole (the test side) or a path
    parameter (the route side).
    """
    path = path.split("?", 1)[0].rstrip("/") or "/"
    return [
        "*" if (HOLE in segment or ("{" in segment and "}" in segment)) else segment
        for segment in path.split("/")
    ]


def _matches(called: list[str], route: list[str]) -> bool:
    """Whether a called path could be served by a route.

    ``*`` is a wildcard on either side: on the route side because the parameter
    accepts anything, on the test side because the value is interpolated.  A
    test that hardcodes an id -- ``/accounts/2147483647`` for a deliberate 404 --
    must still match ``/accounts/{account_id}``.
    """
    if len(called) != len(route):
        return False
    return all(a == b or a == "*" or b == "*" for a, b in zip(called, route))


def _registered() -> list[tuple[str, list[str]]]:
    return [
        (method, _segments(getattr(route, "path", "")))
        for route in app.routes
        for method in getattr(route, "methods", set())
    ]


def _is_served(method: str, called: list[str], registered) -> bool:
    return any(
        method == route_method and _matches(called, route_segments)
        for route_method, route_segments in registered
    )


def test_every_requests_call_in_the_test_tree_is_resolvable():
    """Guard the guard: a call this module cannot read is a call it cannot check."""
    _, unresolved = _call_sites()
    surprises = [
        item for item in unresolved if (item[0], item[1]) not in UNRESOLVABLE_CALL_SITES
    ]
    assert not surprises, (
        "These HTTP call sites could not be resolved to a URL, so the assertion "
        "below silently skips them:\n"
        + "\n".join(f"  {name}:{line}  {detail}" for name, line, detail in surprises)
        + "\nEither express the URL so it can be read statically, or add the site "
        "to UNRESOLVABLE_CALL_SITES with the reason."
    )


def test_unresolvable_allowlist_entries_still_exist():
    """An exemption that no longer describes reality is worse than none."""
    _, unresolved = _call_sites()
    present = {(name, line) for name, line, _ in unresolved}
    stale = sorted(site for site in UNRESOLVABLE_CALL_SITES if site not in present)
    assert not stale, (
        "These UNRESOLVABLE_CALL_SITES entries no longer match an unresolved "
        f"call site and must be removed: {stale}"
    )


def test_known_orphan_allowlist_entries_are_still_orphans():
    """Once a listed call site is fixed, the excuse must go with it."""
    resolved, _ = _call_sites()
    registered = _registered()

    now_served = []
    for name, line, method, template in resolved:
        if (name, line) not in KNOWN_ORPHANED_CALL_SITES or not template.startswith(HOLE):
            continue
        if _is_served(method, _segments(template[len(HOLE):]), registered):
            now_served.append((name, line))

    present = {(name, line) for name, line, _, _ in resolved}
    vanished = sorted(site for site in KNOWN_ORPHANED_CALL_SITES if site not in present)

    assert not now_served and not vanished, (
        "KNOWN_ORPHANED_CALL_SITES is stale and must be trimmed. "
        f"Now resolving to a real route: {sorted(now_served)}. "
        f"No longer present at all: {vanished}."
    )


def test_no_test_calls_a_route_the_app_does_not_serve():
    resolved, _ = _call_sites()
    registered = _registered()

    orphans = []
    for name, line, method, template in resolved:
        if not template.startswith(HOLE):
            continue  # not a call against the application under test
        if (name, line) in KNOWN_ORPHANED_CALL_SITES:
            continue
        called = _segments(template[len(HOLE):])
        if not _is_served(method, called, registered):
            orphans.append(f"  {name}:{line}  {method} {'/'.join(called)}")

    assert not orphans, (
        "These tests call endpoints the application does not register:\n"
        + "\n".join(sorted(orphans))
        + "\n\nA deleted route leaves its callers behind, and they fail only when "
        "someone runs the stack. Migrate the call site, or restore the route."
    )
