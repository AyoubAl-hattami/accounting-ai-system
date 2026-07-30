from datetime import date

from app.application.reports.dto import (
    AccountLedgerQuery,
    BalanceSheetQuery,
    GeneralLedgerQuery,
    ProfitAndLossQuery,
    TrialBalanceQuery,
)
from app.application.reports.use_cases import (
    GetAccountLedger,
    GetBalanceSheet,
    GetGeneralLedger,
    GetProfitAndLoss,
    GetTrialBalance,
)


class RecordingReportRepository:
    def __init__(self):
        self.calls = []
        self.results = {
            "trial": object(),
            "profit": object(),
            "balance": object(),
            "account": object(),
            "general": object(),
        }

    def get_trial_balance(self, query):
        self.calls.append(("trial", query))
        return self.results["trial"]

    def get_profit_and_loss(self, query):
        self.calls.append(("profit", query))
        return self.results["profit"]

    def get_balance_sheet(self, query):
        self.calls.append(("balance", query))
        return self.results["balance"]

    def get_account_ledger(self, query):
        self.calls.append(("account", query))
        return self.results["account"]

    def get_general_ledger(self, query):
        self.calls.append(("general", query))
        return self.results["general"]


def test_report_use_cases_delegate_exact_framework_neutral_queries():
    repository = RecordingReportRepository()
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    trial = TrialBalanceQuery(company_id=3, as_of_date=end)
    profit = ProfitAndLossQuery(company_id=3, start_date=start, end_date=end)
    balance = BalanceSheetQuery(company_id=3, as_of_date=end)
    account = AccountLedgerQuery(
        company_id=3, account_id=10, start_date=start, end_date=end
    )
    general = GeneralLedgerQuery(company_id=3, start_date=start, end_date=end)

    assert GetTrialBalance(repository).execute(trial) is repository.results["trial"]
    assert GetProfitAndLoss(repository).execute(profit) is repository.results["profit"]
    assert GetBalanceSheet(repository).execute(balance) is repository.results["balance"]
    assert GetAccountLedger(repository).execute(account) is repository.results["account"]
    assert GetGeneralLedger(repository).execute(general) is repository.results["general"]
    assert repository.calls == [
        ("trial", trial),
        ("profit", profit),
        ("balance", balance),
        ("account", account),
        ("general", general),
    ]