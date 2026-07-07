"""
Safe company data reset script for local development.

Clears operational/accounting data for ONE selected company while
preserving structural data (users, accounts, fiscal config).

Usage:
    cd C:\\ayoub\\accounting-ai-system\\backend
    .venv\\Scripts\\activate
    $env:PYTHONPATH = "C:\\ayoub\\accounting-ai-system\\backend"
    python scripts/reset_company_data.py --company-id 3 --confirm RESET

Without --confirm RESET, prints what WOULD be deleted (dry run).
"""

import argparse
import sys

from sqlalchemy import text

# ── Bootstrap the app so we can use SessionLocal / models ─────────────────────
from app.core.database import SessionLocal
from app.modules.accounting.models.company import Company


def _list_companies():
    """Print available companies and exit."""
    db = SessionLocal()
    try:
        companies = db.query(Company).order_by(Company.id).all()
        if not companies:
            print("No companies found in the database.")
            return
        print("\nAvailable companies:")
        print(f"  {'ID':>5}  {'Name':<40}  {'Created'}")
        print("  " + "-" * 70)
        for c in companies:
            print(f"  {c.id:>5}  {c.name:<40}  {c.created_at}")
        print()
    finally:
        db.close()


def _count(db, table: str, company_id: int, extra_where: str = "") -> int:
    """Count rows in a table filtered by company_id."""
    where = f"company_id = :cid"
    if extra_where:
        where += f" AND {extra_where}"
    result = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), {"cid": company_id})
    return result.scalar()


def _delete(db, table: str, company_id: int, extra_where: str = "") -> int:
    """Delete rows in a table filtered by company_id. Returns deleted count."""
    where = f"company_id = :cid"
    if extra_where:
        where += f" AND {extra_where}"
    result = db.execute(text(f"DELETE FROM {table} WHERE {where}"), {"cid": company_id})
    return result.rowcount


def reset_company_data(company_id: int, confirm: bool = False):
    """
    Reset operational data for a single company.

    Deletes (in FK-safe order):
      1. journal_lines
      2. journal_entries
      3. audit_logs
      4. company_user_invitations (pending only — accepted_at IS NULL)

    Preserves:
      - users, companies, company_users
      - accounts (chart of accounts)
      - fiscal_years, fiscal_periods
    """
    db = SessionLocal()
    try:
        # Verify company exists
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            print(f"\n✗ Company with ID {company_id} not found.")
            _list_companies()
            sys.exit(1)

        print(f"\n{'=' * 60}")
        print(f"  Company: {company.name} (ID: {company.id})")
        print(f"{'=' * 60}")

        # Tables to clear, in FK-safe deletion order
        tables = [
            ("journal_lines", ""),
            ("journal_entries", ""),
            ("audit_logs", ""),
            ("company_user_invitations", "accepted_at IS NULL"),
        ]

        counts = {}
        for table, extra in tables:
            counts[table] = _count(db, table, company_id, extra)

        # Print summary
        label = "WILL DELETE" if confirm else "Would delete (dry run)"
        print(f"\n  {label}:")
        for table, _ in tables:
            suffix = " (pending only)" if table == "company_user_invitations" else ""
            print(f"    {table:<35} {counts[table]:>6} rows{suffix}")

        preserved = [
            "users", "companies", "company_users",
            "accounts", "fiscal_years", "fiscal_periods",
        ]
        print(f"\n  Preserved (not deleted):")
        for table in preserved:
            print(f"    ✓ {table}")

        if not confirm:
            print(f"\n  ⚠ Dry run — no data was deleted.")
            print(f"  To execute, add: --confirm RESET\n")
            return counts

        # Execute deletions in FK-safe order
        print(f"\n  Executing reset...")
        deleted = {}
        for table, extra in tables:
            deleted[table] = _delete(db, table, company_id, extra)

        db.commit()

        print(f"\n  ✅ Reset complete:")
        for table, _ in tables:
            print(f"    {table:<35} {deleted[table]:>6} rows deleted")

        print(f"\n  Dashboard financial totals will now be zero.")
        print(f"  Reports will show zero.")
        print(f"  Accounts and fiscal periods are untouched.\n")

        return deleted

    except Exception as e:
        db.rollback()
        print(f"\n  ✗ Error during reset: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reset operational/accounting data for a single company.",
    )
    parser.add_argument(
        "--company-id",
        type=int,
        default=None,
        help="ID of the company to reset. If omitted, lists available companies.",
    )
    parser.add_argument(
        "--confirm",
        type=str,
        default=None,
        help="Must be 'RESET' to execute. Without this flag, performs a dry run.",
    )

    args = parser.parse_args()

    if args.company_id is None:
        print("\n  --company-id is required.")
        _list_companies()
        sys.exit(0)

    confirmed = args.confirm == "RESET"
    if args.confirm and args.confirm != "RESET":
        print(f"\n  ✗ Invalid --confirm value: '{args.confirm}'. Must be exactly 'RESET'.")
        sys.exit(1)

    reset_company_data(company_id=args.company_id, confirm=confirmed)


if __name__ == "__main__":
    main()
