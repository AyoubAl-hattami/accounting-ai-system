from dataclasses import asdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.reports.dto import (
    AccountLedgerQuery,
    BalanceSheetQuery,
    GeneralLedgerQuery,
    ProfitAndLossQuery,
    TrialBalanceQuery,
)
from app.application.reports.errors import MissingFiscalYearForReportError
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.services import report_service


class CountingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()


def _entry(company_id, number, entry_date, status, fiscal_year_id, lines):
    entry = JournalEntry(
        company_id=company_id,
        fiscal_year_id=fiscal_year_id,
        fiscal_period_id=1,
        entry_no=number,
        entry_date=entry_date,
        status=status,
    )
    entry.lines = [
        JournalLine(
            company_id=company_id,
            account_id=account_id,
            line_no=index,
            debit=debit,
            credit=credit,
        )
        for index, (account_id, debit, credit) in enumerate(lines, start=1)
    ]
    return entry


def _legacy_dict(result):
    return result.model_dump(mode="python") if result is not None else None


def test_sqlalchemy_report_repository_matches_every_legacy_report_and_never_commits():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (
        FiscalYear.__table__,
        Account.__table__,
        JournalEntry.__table__,
        JournalLine.__table__,
    ):
        table.create(engine)
    try:
        with CountingSession(engine) as db:
            year = FiscalYear(
                company_id=1,
                name="FY 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="open",
            )
            db.add(year)
            db.flush()
            accounts = [
                Account(
                    company_id=company_id,
                    code=code,
                    name=name,
                    account_type=account_type,
                    is_active=True,
                    is_system=False,
                )
                for company_id, code, name, account_type in (
                    (1, "1000", "Cash", "asset"),
                    (1, "2000", "Payables", "liability"),
                    (1, "3000", "Capital", "equity"),
                    (1, "4000", "Revenue", "income"),
                    (1, "5000", "Expense", "expense"),
                    (2, "1000", "Foreign Cash", "asset"),
                )
            ]
            db.add_all(accounts)
            db.flush()
            cash, _liability, _equity, income, expense, foreign_cash = accounts
            db.add_all(
                [
                    _entry(
                        1,
                        "PRIOR",
                        date(2025, 12, 31),
                        "posted",
                        year.id,
                        [
                            (cash.id, Decimal("100.00"), Decimal("0.00")),
                            (income.id, Decimal("0.00"), Decimal("100.00")),
                        ],
                    ),
                    _entry(
                        1,
                        "POSTED",
                        date(2026, 1, 10),
                        "posted",
                        year.id,
                        [
                            (cash.id, Decimal("1000.00"), Decimal("0.00")),
                            (income.id, Decimal("0.00"), Decimal("1000.00")),
                        ],
                    ),
                    _entry(
                        1,
                        "REVERSED",
                        date(2026, 1, 11),
                        "reversed",
                        year.id,
                        [
                            (expense.id, Decimal("100.00"), Decimal("0.00")),
                            (cash.id, Decimal("0.00"), Decimal("100.00")),
                        ],
                    ),
                    _entry(
                        1,
                        "DRAFT",
                        date(2026, 1, 12),
                        "draft",
                        year.id,
                        [
                            (expense.id, Decimal("999.00"), Decimal("0.00")),
                            (cash.id, Decimal("0.00"), Decimal("999.00")),
                        ],
                    ),
                    _entry(
                        2,
                        "FOREIGN",
                        date(2026, 1, 10),
                        "posted",
                        year.id,
                        [
                            (foreign_cash.id, Decimal("700.00"), Decimal("0.00")),
                        ],
                    ),
                ]
            )
            db.commit()
            db.commit_calls = 0
            repository = SqlAlchemyReportRepository(db)
            start = date(2026, 1, 1)
            end = date(2026, 1, 31)

            trial = repository.get_trial_balance(
                TrialBalanceQuery(company_id=1, as_of_date=end)
            )
            legacy_trial = report_service.get_trial_balance(db, 1, end)
            assert asdict(trial) == _legacy_dict(legacy_trial)
            assert [line.account_code for line in trial.lines] == [
                "1000", "2000", "3000", "4000", "5000"
            ]

            profit = repository.get_profit_and_loss(
                ProfitAndLossQuery(company_id=1, start_date=start, end_date=end)
            )
            assert asdict(profit) == _legacy_dict(
                report_service.get_profit_and_loss(db, 1, start, end)
            )
            assert profit.total_income == Decimal("1000.00")
            assert profit.total_expenses == Decimal("100.00")

            balance = repository.get_balance_sheet(
                BalanceSheetQuery(company_id=1, as_of_date=end)
            )
            assert asdict(balance) == _legacy_dict(
                report_service.get_balance_sheet(db, 1, end)
            )
            assert balance.prior_year_earnings == Decimal("100.00")
            assert balance.current_year_earnings == Decimal("900.00")
            assert balance.is_balanced is True

            account = repository.get_account_ledger(
                AccountLedgerQuery(
                    company_id=1,
                    account_id=cash.id,
                    start_date=start,
                    end_date=end,
                )
            )
            assert asdict(account) == _legacy_dict(
                report_service.get_account_ledger(db, 1, cash.id, start, end)
            )
            assert account.opening_balance == Decimal("100.00")
            assert [line.entry_no for line in account.lines] == [
                "POSTED", "REVERSED"
            ]
            assert account.closing_balance == Decimal("1000.00")

            general = repository.get_general_ledger(
                GeneralLedgerQuery(company_id=1, start_date=start, end_date=end)
            )
            assert asdict(general) == _legacy_dict(
                report_service.get_general_ledger(db, 1, start, end)
            )
            assert [ledger.account_code for ledger in general.accounts] == [
                "1000", "2000", "3000", "4000", "5000"
            ]

            missing = repository.get_account_ledger(
                AccountLedgerQuery(company_id=1, account_id=foreign_cash.id)
            )
            assert missing is None
            assert db.commit_calls == 0

            with pytest.raises(
                MissingFiscalYearForReportError,
                match="No fiscal year covers the selected date.",
            ):
                repository.get_balance_sheet(
                    BalanceSheetQuery(
                        company_id=1,
                        as_of_date=date(2030, 1, 1),
                    )
                )
            assert db.commit_calls == 0
    finally:
        engine.dispose()