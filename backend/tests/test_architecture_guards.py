"""Static guards for the backend Clean Architecture dependency boundary."""

from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = BACKEND_ROOT / "app" / "application"
REPOSITORY_ROOT = (
    BACKEND_ROOT
    / "app"
    / "infrastructure"
    / "database"
    / "sqlalchemy"
    / "repositories"
)
ROUTES_ROOT = BACKEND_ROOT / "app" / "modules" / "accounting" / "routes"

FORBIDDEN_APPLICATION_IMPORT_PREFIXES = (
    "fastapi",
    "sqlalchemy",
    "app.modules.accounting.models",
    "app.modules.accounting.schemas",
    "openai",
    "google.genai",
    "google.generativeai",
)
FORBIDDEN_APPLICATION_IMPORTED_NAMES = frozenset(
    {"Request", "Depends", "HTTPException", "Session", "genai", "OpenAI"}
)
FORBIDDEN_APPLICATION_SESSION_CALLS = frozenset(
    {"commit", "flush", "add", "delete"}
)
FORBIDDEN_REPOSITORY_IMPORT_PREFIXES = ("fastapi",)
FORBIDDEN_REPOSITORY_NAMES = frozenset(
    {"Request", "Depends", "HTTPException"}
)
REPORT_FORBIDDEN_CALLS = frozenset({"commit", "flush", "add", "delete"})
JOURNAL_DIRECT_FLUSH_METHODS = frozenset(
    {
        "create",
        "create_opening_balance",
        "update",
        "review",
        "post",
        "void",
        "reverse",
    }
)


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts
    )


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_records(path: Path) -> list[tuple[int, str, str]]:
    records: list[tuple[int, str, str]] = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            records.extend(
                (node.lineno, alias.name, alias.asname or alias.name)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            records.extend(
                (node.lineno, module, alias.asname or alias.name)
                for alias in node.names
            )
    return records


def _attribute_calls(path: Path) -> list[tuple[int, str]]:
    return [
        (node.lineno, node.func.attr)
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]


def _format_failures(failures: list[str]) -> str:
    return "\n" + "\n".join(failures)


def test_application_layer_has_no_forbidden_framework_or_adapter_imports():
    failures: list[str] = []
    for path in _python_files(APPLICATION_ROOT):
        for lineno, module, imported_name in _import_records(path):
            if module.startswith(FORBIDDEN_APPLICATION_IMPORT_PREFIXES):
                failures.append(f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {module}")
            if imported_name in FORBIDDEN_APPLICATION_IMPORTED_NAMES:
                failures.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {imported_name}"
                )

    assert not failures, _format_failures(failures)


def test_application_layer_has_no_database_session_mutations():
    failures = [
        f"{path.relative_to(BACKEND_ROOT)}:{lineno}: .{method}()"
        for path in _python_files(APPLICATION_ROOT)
        for lineno, method in _attribute_calls(path)
        if method in FORBIDDEN_APPLICATION_SESSION_CALLS
    ]

    assert not failures, _format_failures(failures)


def test_repositories_have_no_http_dependencies_or_commits():
    failures: list[str] = []
    for path in _python_files(REPOSITORY_ROOT):
        for lineno, module, imported_name in _import_records(path):
            if module.startswith(FORBIDDEN_REPOSITORY_IMPORT_PREFIXES):
                failures.append(f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {module}")
            if imported_name in FORBIDDEN_REPOSITORY_NAMES:
                failures.append(
                    f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {imported_name}"
                )
        failures.extend(
            f"{path.relative_to(BACKEND_ROOT)}:{lineno}: .commit()"
            for lineno, method in _attribute_calls(path)
            if method == "commit"
        )

    assert not failures, _format_failures(failures)


def test_report_repository_remains_read_only():
    path = REPOSITORY_ROOT / "report_repository.py"
    failures = [
        f"{path.relative_to(BACKEND_ROOT)}:{lineno}: .{method}()"
        for lineno, method in _attribute_calls(path)
        if method in REPORT_FORBIDDEN_CALLS
    ]

    assert not failures, _format_failures(failures)


def test_direct_repository_flushes_stay_in_existing_journal_mutations():
    failures: list[str] = []
    for path in _python_files(REPOSITORY_ROOT):
        tree = _tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            direct_flush_lines = [
                call.lineno
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "flush"
            ]
            for lineno in direct_flush_lines:
                allowed = (
                    path.name == "journal_repository.py"
                    and node.name in JOURNAL_DIRECT_FLUSH_METHODS
                )
                if not allowed:
                    failures.append(
                        f"{path.relative_to(BACKEND_ROOT)}:{lineno}: "
                        f"unexpected flush in {node.name}()"
                    )

    assert not failures, _format_failures(failures)


def test_routes_do_not_import_deleted_legacy_accounting_services():
    deleted_modules = tuple(
        "app.modules.accounting.services." + name
        for name in (
            "account_" + "service",
            "fiscal_" + "service",
            "journal_" + "service",
            "report_" + "service",
            "default_accounts_" + "service",
        )
    )
    failures = [
        f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {module}"
        for path in _python_files(ROUTES_ROOT)
        for lineno, module, _ in _import_records(path)
        if module.startswith(deleted_modules)
    ]

    assert not failures, _format_failures(failures)


def test_backend_has_no_deleted_legacy_accounting_references():
    deleted_tokens = tuple(
        prefix + suffix
        for prefix, suffix in (
            ("account_", "service"),
            ("fiscal_", "service"),
            ("journal_", "service"),
            ("report_", "service"),
            ("default_accounts_", "service"),
            ("Account", "Service"),
            ("Fiscal", "Service"),
            ("Journal", "Service"),
            ("Report", "Service"),
            ("create_default_", "accounts"),
        )
    )
    this_file = Path(__file__).resolve()
    failures: list[str] = []
    for root in (BACKEND_ROOT / "app", BACKEND_ROOT / "tests"):
        for path in _python_files(root):
            if path.resolve() == this_file:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if any(token in line for token in deleted_tokens):
                    failures.append(
                        f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {line.strip()}"
                    )

    assert not failures, _format_failures(failures)
