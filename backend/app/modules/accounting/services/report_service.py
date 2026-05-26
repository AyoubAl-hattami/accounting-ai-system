from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.schemas.report import (
    TrialBalanceLine,
    TrialBalanceRead,
    ProfitAndLossLine,
    ProfitAndLossRead,
    BalanceSheetLine,
    BalanceSheetRead,
    AccountLedgerLine,
    AccountLedgerRead,
    GeneralLedgerRead,
)


def get_trial_balance(
    db: Session,
    company_id: int,
    as_of_date: date | None = None,
) -> TrialBalanceRead:
    posted_filter = JournalEntry.status.in_(["posted", "reversed"])

    if as_of_date is not None:
        posted_filter = posted_filter & (JournalEntry.entry_date <= as_of_date)

    debit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.debit),
                else_=0,
            )
        ),
        0,
    )

    credit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.credit),
                else_=0,
            )
        ),
        0,
    )

    statement = (
        select(
            Account.id.label("account_id"),
            Account.code.label("account_code"),
            Account.name.label("account_name"),
            Account.account_type.label("account_type"),
            debit_sum.label("debit_total"),
            credit_sum.label("credit_total"),
        )
        .select_from(Account)
        .join(
            JournalLine,
            JournalLine.account_id == Account.id,
            isouter=True,
        )
        .join(
            JournalEntry,
            JournalEntry.id == JournalLine.journal_entry_id,
            isouter=True,
        )
        .where(Account.company_id == company_id)
        .group_by(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
        )
        .order_by(Account.code.asc())
    )

    rows = db.execute(statement).all()

    lines: list[TrialBalanceLine] = []

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    total_debit_balance = Decimal("0.00")
    total_credit_balance = Decimal("0.00")

    for row in rows:
        debit_total = Decimal(str(row.debit_total or 0))
        credit_total = Decimal(str(row.credit_total or 0))

        balance = debit_total - credit_total

        if balance >= 0:
            debit_balance = balance
            credit_balance = Decimal("0.00")
        else:
            debit_balance = Decimal("0.00")
            credit_balance = abs(balance)

        total_debit += debit_total
        total_credit += credit_total
        total_debit_balance += debit_balance
        total_credit_balance += credit_balance

        lines.append(
            TrialBalanceLine(
                account_id=row.account_id,
                account_code=row.account_code,
                account_name=row.account_name,
                account_type=row.account_type,
                debit_total=debit_total,
                credit_total=credit_total,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
            )
        )

    return TrialBalanceRead(
        company_id=company_id,
        as_of_date=as_of_date,
        total_debit=total_debit,
        total_credit=total_credit,
        total_debit_balance=total_debit_balance,
        total_credit_balance=total_credit_balance,
        is_balanced=total_debit_balance == total_credit_balance,
        lines=lines,
    )
def get_profit_and_loss(
    db: Session,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ProfitAndLossRead:
    posted_filter = JournalEntry.status.in_(["posted", "reversed"])

    if start_date is not None:
        posted_filter = posted_filter & (JournalEntry.entry_date >= start_date)

    if end_date is not None:
        posted_filter = posted_filter & (JournalEntry.entry_date <= end_date)

    debit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.debit),
                else_=0,
            )
        ),
        0,
    )

    credit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.credit),
                else_=0,
            )
        ),
        0,
    )

    statement = (
        select(
            Account.id.label("account_id"),
            Account.code.label("account_code"),
            Account.name.label("account_name"),
            Account.account_type.label("account_type"),
            debit_sum.label("debit_total"),
            credit_sum.label("credit_total"),
        )
        .select_from(Account)
        .join(
            JournalLine,
            JournalLine.account_id == Account.id,
            isouter=True,
        )
        .join(
            JournalEntry,
            JournalEntry.id == JournalLine.journal_entry_id,
            isouter=True,
        )
        .where(
            Account.company_id == company_id,
            Account.account_type.in_(["income", "expense"]),
        )
        .group_by(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
        )
        .order_by(Account.code.asc())
    )

    rows = db.execute(statement).all()

    income_lines: list[ProfitAndLossLine] = []
    expense_lines: list[ProfitAndLossLine] = []

    total_income = Decimal("0.00")
    total_expenses = Decimal("0.00")

    for row in rows:
        debit_total = Decimal(str(row.debit_total or 0))
        credit_total = Decimal(str(row.credit_total or 0))

        if row.account_type == "income":
            amount = credit_total - debit_total
            total_income += amount

            income_lines.append(
                ProfitAndLossLine(
                    account_id=row.account_id,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    account_type=row.account_type,
                    amount=amount,
                )
            )

        elif row.account_type == "expense":
            amount = debit_total - credit_total
            total_expenses += amount

            expense_lines.append(
                ProfitAndLossLine(
                    account_id=row.account_id,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    account_type=row.account_type,
                    amount=amount,
                )
            )

    net_profit = total_income - total_expenses

    return ProfitAndLossRead(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        income_lines=income_lines,
        expense_lines=expense_lines,
    )
def get_balance_sheet(
    db: Session,
    company_id: int,
    as_of_date: date | None = None,
) -> BalanceSheetRead:
    posted_filter = JournalEntry.status.in_(["posted", "reversed"])

    if as_of_date is not None:
        posted_filter = posted_filter & (JournalEntry.entry_date <= as_of_date)

    debit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.debit),
                else_=0,
            )
        ),
        0,
    )

    credit_sum = func.coalesce(
        func.sum(
            case(
                (posted_filter, JournalLine.credit),
                else_=0,
            )
        ),
        0,
    )

    statement = (
        select(
            Account.id.label("account_id"),
            Account.code.label("account_code"),
            Account.name.label("account_name"),
            Account.account_type.label("account_type"),
            debit_sum.label("debit_total"),
            credit_sum.label("credit_total"),
        )
        .select_from(Account)
        .join(
            JournalLine,
            JournalLine.account_id == Account.id,
            isouter=True,
        )
        .join(
            JournalEntry,
            JournalEntry.id == JournalLine.journal_entry_id,
            isouter=True,
        )
        .where(
            Account.company_id == company_id,
            Account.account_type.in_(["asset", "liability", "equity"]),
        )
        .group_by(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
        )
        .order_by(Account.code.asc())
    )

    rows = db.execute(statement).all()

    asset_lines: list[BalanceSheetLine] = []
    liability_lines: list[BalanceSheetLine] = []
    equity_lines: list[BalanceSheetLine] = []

    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")

    for row in rows:
        debit_total = Decimal(str(row.debit_total or 0))
        credit_total = Decimal(str(row.credit_total or 0))

        if row.account_type == "asset":
            amount = debit_total - credit_total
            total_assets += amount

            asset_lines.append(
                BalanceSheetLine(
                    account_id=row.account_id,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    account_type=row.account_type,
                    amount=amount,
                )
            )

        elif row.account_type == "liability":
            amount = credit_total - debit_total
            total_liabilities += amount

            liability_lines.append(
                BalanceSheetLine(
                    account_id=row.account_id,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    account_type=row.account_type,
                    amount=amount,
                )
            )

        elif row.account_type == "equity":
            amount = credit_total - debit_total
            total_equity += amount

            equity_lines.append(
                BalanceSheetLine(
                    account_id=row.account_id,
                    account_code=row.account_code,
                    account_name=row.account_name,
                    account_type=row.account_type,
                    amount=amount,
                )
            )

    effective_date = as_of_date or date.today()

    fiscal_year = db.scalar(
        select(FiscalYear).where(
            FiscalYear.company_id == company_id,
            FiscalYear.start_date <= effective_date,
            FiscalYear.end_date >= effective_date,
        )
    )

    profit_start_date = fiscal_year.start_date if fiscal_year else None

    profit_and_loss = get_profit_and_loss(
        db=db,
        company_id=company_id,
        start_date=profit_start_date,
        end_date=as_of_date,
    )

    current_year_earnings = profit_and_loss.net_profit

    total_liabilities_and_equity = (
        total_liabilities
        + total_equity
        + current_year_earnings
    )

    return BalanceSheetRead(
        company_id=company_id,
        as_of_date=as_of_date,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        current_year_earnings=current_year_earnings,
        total_liabilities_and_equity=total_liabilities_and_equity,
        is_balanced=total_assets == total_liabilities_and_equity,
        asset_lines=asset_lines,
        liability_lines=liability_lines,
        equity_lines=equity_lines,
    )
def _account_signed_amount(
    account_type: str,
    debit: Decimal,
    credit: Decimal,
) -> Decimal:
    if account_type in {"asset", "expense"}:
        return debit - credit

    return credit - debit


def get_account_ledger(
    db: Session,
    company_id: int,
    account_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AccountLedgerRead | None:
    account = db.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.company_id == company_id,
        )
    )

    if account is None:
        return None

    opening_balance = Decimal("0.00")

    if start_date is not None:
        opening_statement = (
            select(
                func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
            )
            .select_from(JournalLine)
            .join(
                JournalEntry,
                JournalEntry.id == JournalLine.journal_entry_id,
            )
            .where(
                JournalLine.company_id == company_id,
                JournalLine.account_id == account_id,
                JournalEntry.status.in_(["posted", "reversed"]),
                JournalEntry.entry_date < start_date,
            )
        )

        opening_row = db.execute(opening_statement).one()

        opening_debit = Decimal(str(opening_row.debit_total or 0))
        opening_credit = Decimal(str(opening_row.credit_total or 0))

        opening_balance = _account_signed_amount(
            account_type=account.account_type,
            debit=opening_debit,
            credit=opening_credit,
        )

    statement = (
        select(
            JournalEntry.id.label("journal_entry_id"),
            JournalEntry.entry_no.label("entry_no"),
            JournalEntry.entry_date.label("entry_date"),
            JournalLine.line_no.label("line_no"),
            JournalLine.description.label("description"),
            JournalLine.debit.label("debit"),
            JournalLine.credit.label("credit"),
        )
        .select_from(JournalLine)
        .join(
            JournalEntry,
            JournalEntry.id == JournalLine.journal_entry_id,
        )
        .where(
            JournalLine.company_id == company_id,
            JournalLine.account_id == account_id,
            JournalEntry.status.in_(["posted", "reversed"]),
        )
        .order_by(
            JournalEntry.entry_date.asc(),
            JournalEntry.id.asc(),
            JournalLine.line_no.asc(),
        )
    )

    if start_date is not None:
        statement = statement.where(JournalEntry.entry_date >= start_date)

    if end_date is not None:
        statement = statement.where(JournalEntry.entry_date <= end_date)

    rows = db.execute(statement).all()

    running_balance = opening_balance
    lines: list[AccountLedgerLine] = []

    for row in rows:
        debit = Decimal(str(row.debit or 0))
        credit = Decimal(str(row.credit or 0))

        movement = _account_signed_amount(
            account_type=account.account_type,
            debit=debit,
            credit=credit,
        )

        running_balance += movement

        lines.append(
            AccountLedgerLine(
                journal_entry_id=row.journal_entry_id,
                entry_no=row.entry_no,
                entry_date=row.entry_date,
                line_no=row.line_no,
                description=row.description,
                debit=debit,
                credit=credit,
                running_balance=running_balance,
            )
        )

    return AccountLedgerRead(
        company_id=company_id,
        account_id=account.id,
        account_code=account.code,
        account_name=account.name,
        account_type=account.account_type,
        start_date=start_date,
        end_date=end_date,
        opening_balance=opening_balance,
        closing_balance=running_balance,
        lines=lines,
    )
def get_general_ledger(
    db: Session,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> GeneralLedgerRead:
    accounts = db.scalars(
        select(Account)
        .where(Account.company_id == company_id)
        .order_by(Account.code.asc())
    ).all()

    account_ledgers: list[AccountLedgerRead] = []

    for account in accounts:
        ledger = get_account_ledger(
            db=db,
            company_id=company_id,
            account_id=account.id,
            start_date=start_date,
            end_date=end_date,
        )

        if ledger is not None:
            account_ledgers.append(ledger)

    return GeneralLedgerRead(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        accounts=account_ledgers,
    )