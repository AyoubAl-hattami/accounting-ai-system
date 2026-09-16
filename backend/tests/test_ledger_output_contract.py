"""The ledger output contract: every figure, every ordering, pinned.

The account ledger and the general ledger are what an accountant reconciles
against. When [C3] replaced the per-account loop with grouped queries and [D3]
added pagination, the thing that had to be proved was not that the tests still
passed -- it was that not one number moved.

HOW THIS WORKS. A fixed fixture is built under a fresh company, the ledgers are
produced over six date windows, and the result is compared field by field with
a golden file. The comparison is a PROJECTION: surrogate ids and the company id
are replaced by stable keys (account code, entry number), because those move
between databases and say nothing about the figures.

WHY A PROJECTION AND NOT A HASH OF THE WHOLE PAYLOAD. [D3] added six fields to
the ledger DTOs. A whole-payload hash changed the moment the schema grew, which
tells a reader nothing about whether the money changed -- and a test that has to
be re-blessed on every schema addition stops being read. This one survives a
new field and still fails on a cent.

Decimals are compared as STRINGS. "900.00", "900.0" and "900" are three
different results here, deliberately: a lost trailing zero is a rendering change
an accountant's diff would show.
"""

import json
import pathlib
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from app.modules.accounting.services.reports_application_facade import (
    get_account_ledger,
    get_general_ledger,
)

GOLDEN = pathlib.Path(__file__).resolve().parent / "fixtures" / "ledger_contract.json"

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

ACCOUNTS = [
    ("1000", "Cash at Bank", "asset"),
    ("1100", "Accounts Receivable", "asset"),
    ("1200", "Prepaid Rent", "asset"),       # non-zero opening, no Q2 movement
    ("1900", "Dormant Asset", "asset"),      # no movement, ever
    ("2000", "Accounts Payable", "liability"),
    ("4000", "Consulting Revenue", "income"),
    ("4900", "Dormant Revenue", "income"),   # no movement, ever
    ("5000", "Rent Expense", "expense"),
    ("5100", "Salaries Expense", "expense"),
]

ENTRIES = [
    ("JE-0001", date(2026, 1, 5), "posted", [
        ("1000", "25000.00", "0.00", "Owner funding"),
        ("2000", "0.00", "25000.00", "Owner funding")]),
    ("JE-0002", date(2026, 1, 20), "posted", [
        ("1200", "3600.00", "0.00", "Twelve months rent paid up front"),
        ("1000", "0.00", "3600.00", "Twelve months rent paid up front")]),
    ("JE-0003", date(2026, 2, 11), "posted", [
        ("1100", "8400.50", "0.00", "Invoice 2026-011"),
        ("4000", "0.00", "8400.50", "Invoice 2026-011")]),
    # A reversed entry and its reversal. Both statuses are reportable, so both
    # appear and their amounts cancel; dropping either would move every running
    # balance after it.
    ("JE-0004", date(2026, 2, 25), "reversed", [
        ("5100", "5000.00", "0.00", "February salaries, later reversed"),
        ("1000", "0.00", "5000.00", "February salaries, later reversed")]),
    ("JE-0005", date(2026, 2, 26), "posted", [
        ("1000", "5000.00", "0.00", "Reversal of JE-0004"),
        ("5100", "0.00", "5000.00", "Reversal of JE-0004")]),
    ("JE-0006", date(2026, 3, 31), "posted", [
        ("5000", "900.00", "0.00", "Q1 rent expensed"),
        ("1200", "0.00", "900.00", "Q1 rent expensed")]),
    # Not reportable: must never appear in a ledger.
    ("JE-0007", date(2026, 3, 15), "draft", [
        ("5100", "1234.56", "0.00", "Draft, must not appear"),
        ("1000", "0.00", "1234.56", "Draft, must not appear")]),
    ("JE-0008", date(2026, 3, 16), "void", [
        ("5100", "7777.77", "0.00", "Void, must not appear"),
        ("1000", "0.00", "7777.77", "Void, must not appear")]),
    # --- the period boundary splits 1000 / 1100 / 4000 ---
    ("JE-0009", date(2026, 4, 2), "posted", [
        ("1000", "8400.50", "0.00", "Invoice 2026-011 settled"),
        ("1100", "0.00", "8400.50", "Invoice 2026-011 settled")]),
    ("JE-0010", date(2026, 5, 18), "posted", [
        ("1100", "12750.25", "0.00", "Invoice 2026-042"),
        ("4000", "0.00", "12750.25", "Invoice 2026-042")]),
    ("JE-0011", date(2026, 6, 30), "posted", [
        ("5100", "6100.00", "0.00", "Q2 salaries"),
        ("1000", "0.00", "6100.00", "Q2 salaries")]),
]

WINDOWS = [
    ("unbounded", None, None),
    ("Q1", date(2026, 1, 1), date(2026, 3, 31)),
    ("Q2", date(2026, 4, 1), date(2026, 6, 30)),
    ("mid-Q1 split", date(2026, 2, 1), date(2026, 2, 28)),
    ("from Q2 start only", date(2026, 4, 1), None),
    ("empty future", date(2026, 11, 1), date(2026, 12, 31)),
]


def _build(db) -> tuple[int, dict[str, int]]:
    """Additive: a fresh company, never a truncate. This runs against the same
    database as the rest of the suite."""
    company = Company(name="Ledger Contract Co", base_currency="USD", is_active=True)
    user = User(email=f"ledger-contract-{id(db)}@fixture.test",
                hashed_password="x", is_active=True, full_name="Contract")
    db.add_all([company, user])
    db.flush()

    year = FiscalYear(company_id=company.id, name="FY2026",
                      start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
                      status="open")
    db.add(year)
    db.flush()

    periods = {}
    for number, (name, start, end) in enumerate(
        [("Q1", date(2026, 1, 1), date(2026, 3, 31)),
         ("Q2", date(2026, 4, 1), date(2026, 6, 30))], start=1
    ):
        period = FiscalPeriod(company_id=company.id, fiscal_year_id=year.id,
                              period_no=number, name=name, start_date=start,
                              end_date=end, status="open")
        db.add(period)
        db.flush()
        periods[name] = period

    accounts = {}
    for code, name, kind in ACCOUNTS:
        account = Account(company_id=company.id, code=code, name=name,
                          account_type=kind, is_active=True, is_system=False)
        db.add(account)
        db.flush()
        accounts[code] = account

    for entry_no, entry_date, status, lines in ENTRIES:
        period = periods["Q1"] if entry_date <= date(2026, 3, 31) else periods["Q2"]
        entry = JournalEntry(
            company_id=company.id, fiscal_year_id=year.id,
            fiscal_period_id=period.id, entry_no=entry_no, entry_date=entry_date,
            status=status, description=f"Contract {entry_no}",
            created_by_user_id=user.id, created_at=T0, updated_at=T0,
        )
        entry.lines = [
            JournalLine(company_id=company.id, account_id=accounts[code].id,
                        line_no=index, debit=Decimal(debit), credit=Decimal(credit),
                        description=description, created_at=T0, updated_at=T0)
            for index, (code, debit, credit, description) in enumerate(lines, start=1)
        ]
        db.add(entry)
        db.flush()

    db.commit()
    return company.id, {code: account.id for code, account in accounts.items()}


def _project_line(line) -> dict:
    """One ledger line, with the surrogate entry id replaced by its number."""
    return {
        "entry_no": line.entry_no,
        "entry_date": line.entry_date.isoformat(),
        "line_no": line.line_no,
        "description": line.description,
        "debit": str(line.debit),
        "credit": str(line.credit),
        "running_balance": str(line.running_balance),
    }


def _project_ledger(ledger) -> dict | None:
    if ledger is None:
        return None
    return {
        "account_code": ledger.account_code,
        "account_name": ledger.account_name,
        "account_type": ledger.account_type,
        "start_date": ledger.start_date.isoformat() if ledger.start_date else None,
        "end_date": ledger.end_date.isoformat() if ledger.end_date else None,
        "opening_balance": str(ledger.opening_balance),
        "closing_balance": str(ledger.closing_balance),
        "lines": [_project_line(line) for line in ledger.lines],
    }


def build_projection(db, company_id: int, accounts: dict[str, int]) -> dict:
    """The contract: every figure and every ordering, no surrogate ids.

    Pagination arguments are deliberately ABSENT from every call, so this
    describes the whole ledger and cannot be satisfied by a page.
    """
    projection: dict = {"accounts": {}, "general": {}}
    for label, start, end in WINDOWS:
        projection["accounts"][label] = {
            code: _project_ledger(
                get_account_ledger(db=db, company_id=company_id, account_id=account_id,
                                   start_date=start, end_date=end)
            )
            for code, account_id in sorted(accounts.items())
        }
        general = get_general_ledger(db=db, company_id=company_id,
                                     start_date=start, end_date=end)
        projection["general"][label] = [
            _project_ledger(ledger) for ledger in general.accounts
        ]
    return projection


@pytest.fixture(scope="module")
def ledger_projection():
    with SessionLocal() as db:
        company_id, accounts = _build(db)
        yield build_projection(db, company_id, accounts)


def test_ledger_output_matches_the_recorded_contract(ledger_projection):
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))

    # Compared window by window so a failure names where it moved rather than
    # dumping the whole ledger.
    assert sorted(ledger_projection["accounts"]) == sorted(expected["accounts"])
    for window in sorted(expected["accounts"]):
        assert ledger_projection["accounts"][window] == expected["accounts"][window], (
            f"account ledgers changed in window {window!r}"
        )
    for window in sorted(expected["general"]):
        assert ledger_projection["general"][window] == expected["general"][window], (
            f"general ledger changed in window {window!r}"
        )


def test_the_contract_covers_what_it_claims(ledger_projection):
    """Guard the guard: a golden file taken from a fixture that misses the
    interesting cases is a weaker contract than it looks."""
    accounts = ledger_projection["accounts"]

    for code in ("1900", "4900"):
        assert all(not accounts[w][code]["lines"] for w in accounts), code
        assert all(Decimal(accounts[w][code]["closing_balance"]) == 0 for w in accounts), code

    q2_prepaid = accounts["Q2"]["1200"]
    assert q2_prepaid["opening_balance"] == "2700.00"
    assert q2_prepaid["lines"] == []
    assert q2_prepaid["closing_balance"] == q2_prepaid["opening_balance"]

    salaries = [line["entry_no"] for line in accounts["Q1"]["5100"]["lines"]]
    assert "JE-0004" in salaries and "JE-0005" in salaries
    assert Decimal(accounts["Q1"]["5100"]["closing_balance"]) == 0

    everywhere = {
        line["entry_no"]
        for window in accounts.values()
        for ledger in window.values()
        for line in ledger["lines"]
    }
    assert "JE-0007" not in everywhere, "a draft entry reached a ledger"
    assert "JE-0008" not in everywhere, "a void entry reached a ledger"

    cash = accounts["unbounded"]["1000"]["lines"]
    assert len(accounts["Q1"]["1000"]["lines"]) + len(accounts["Q2"]["1000"]["lines"]) == len(cash)
    assert accounts["Q2"]["1000"]["opening_balance"] == accounts["Q1"]["1000"]["closing_balance"]
