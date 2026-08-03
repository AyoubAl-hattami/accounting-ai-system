"""Static inventory for deterministic backend fixture migration readiness."""

from __future__ import annotations

import ast
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = TESTS_ROOT.parent
REPOSITORY_ROOT = BACKEND_ROOT.parent

FULL_SUITE_CI_READY = False

SHARED_FIXTURE_NAMES = frozenset(
    {
        "admin_headers",
        "default_company_id",
        "default_bank_account_id",
        "default_owner_capital_account_id",
    }
)
FIXED_SEED_STRINGS = frozenset({"admin@example.com"})
FIXED_SEED_ASSIGNMENTS = {
    "COMPANY_ID": 3,
    "BANK_ACCOUNT_ID": 5,
    "OWNER_CAPITAL_ACCOUNT_ID": 11,
    "ACCOUNT_ID": 5,
    "FISCAL_YEAR_ID_WITH_ENTRIES": 2,
}

EXPECTED_HTTP_INTEGRATION_FILES = frozenset(
    {
        "api/test_company_user_invitations.py",
        "test_ai_status.py",
        "test_ai_suggestions.py",
        "test_assistant_conversations.py",
        "test_auth.py",
        "test_auth_rate_limit.py",
        "test_balance_sheet_multi_year.py",
        "test_client_onboarding.py",
        "test_dashboard_net_income.py",
        "test_default_accounts_seed.py",
        "test_fiscal_management.py",
        "test_fiscal_year_date_protection.py",
        "test_gemini_assistant.py",
        "test_gemini_assistant_explain.py",
        "test_gemini_assistant_profit.py",
        "test_health.py",
        "test_invitation_lifecycle_integrity.py",
        "test_journal_lifecycle_policy.py",
        "test_non_journal_audit_logs.py",
        "test_onboard_client_script.py",
        "test_opening_balance_workflow.py",
        "test_password_policy.py",
        "test_platform_subscriptions.py",
        "test_protected_accounts.py",
        "test_protected_audit_logs.py",
        "test_protected_companies.py",
        "test_protected_company_users.py",
        "test_protected_fiscal.py",
        "test_protected_journal_entries.py",
        "test_protected_reports.py",
        "test_rbac_permission_matrix.py",
        "test_report_csv_exports.py",
        "test_report_pdf_exports.py",
        "test_reports_smoke.py",
        "test_reset_script.py",
        "test_semantic_transaction.py",
    }
)

EXPECTED_IMPLICIT_SEED_CONSUMERS = frozenset()

EXPECTED_SELF_CONTAINED_HTTP_FILES = frozenset(
    {
        "test_auth.py",
        "test_auth_rate_limit.py",
        "test_health.py",
        "test_password_policy.py",
    }
)

EXPECTED_FACTORY_BACKED_HTTP_FILES = frozenset(
    {
        "api/test_company_user_invitations.py",
        "test_ai_status.py",
        "test_ai_suggestions.py",
        "test_default_accounts_seed.py",
        "test_fiscal_management.py",
        "test_fiscal_year_date_protection.py",
        "test_journal_lifecycle_policy.py",
        "test_non_journal_audit_logs.py",
        "test_opening_balance_workflow.py",
        "test_protected_accounts.py",
        "test_protected_audit_logs.py",
        "test_protected_companies.py",
        "test_protected_fiscal.py",
        "test_protected_reports.py",
        "test_rbac_permission_matrix.py",
        "test_report_csv_exports.py",
        "test_report_pdf_exports.py",
        "test_reports_smoke.py",
        "test_dashboard_net_income.py",
        "test_protected_company_users.py",
        "test_protected_journal_entries.py",
        "test_reset_script.py",
        "test_balance_sheet_multi_year.py",
        "test_invitation_lifecycle_integrity.py",
        "test_gemini_assistant_explain.py",
        "test_gemini_assistant_profit.py",
        "test_semantic_transaction.py",
        "test_gemini_assistant.py",
        "test_assistant_conversations.py",
        "test_platform_subscriptions.py",
        "test_client_onboarding.py",
        "test_onboard_client_script.py",
    }
)

EXPECTED_DIRECT_SESSION_FILES = frozenset(
    {
        "test_assistant_conversations.py",
        "test_invitation_lifecycle_integrity.py",
        "test_protected_accounts.py",
        "test_protected_company_users.py",
        "test_protected_journal_entries.py",
    }
)

MOCKED_EXTERNAL_PROVIDER_FILES = frozenset(
    {
        "test_ai_provider_factory.py",
        "test_gemini_agent_contract.py",
        "test_semantic_transaction.py",
    }
)


def _test_files() -> list[Path]:
    return sorted(
        path
        for path in TESTS_ROOT.rglob("test_*.py")
        if path.name != "test_fixture_readiness.py"
    )


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _relative(path: Path) -> str:
    return path.relative_to(TESTS_ROOT).as_posix()


def discover_http_integration_files() -> frozenset[str]:
    matches: set[str] = set()
    for path in _test_files():
        tree = _tree(path)
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "requests"
            for node in ast.walk(tree)
        ):
            matches.add(_relative(path))
    return frozenset(matches)


def discover_implicit_seed_consumers() -> frozenset[str]:
    matches: set[str] = set()
    for path in _test_files():
        tree = _tree(path)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        fixed_assignment = False
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not isinstance(node.value, ast.Constant):
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and FIXED_SEED_ASSIGNMENTS.get(target.id) == node.value.value
                ):
                    fixed_assignment = True

        if (
            names & SHARED_FIXTURE_NAMES
            or strings & FIXED_SEED_STRINGS
            or fixed_assignment
        ):
            matches.add(_relative(path))
    return frozenset(matches)


def discover_direct_session_files() -> frozenset[str]:
    matches: set[str] = set()
    for path in _test_files():
        if any(
            isinstance(node, ast.Name) and node.id == "SessionLocal"
            for node in ast.walk(_tree(path))
        ):
            matches.add(_relative(path))
    return frozenset(matches)
