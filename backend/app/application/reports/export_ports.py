"""Export renderer ports for accounting reports.

Ports are defined as ``typing.Protocol`` so the application layer stays
framework-neutral.  Infrastructure adapters implement these protocols under
``infrastructure/exports/``.
"""

from __future__ import annotations

from typing import Protocol

from app.application.reports.dto import (
    AccountLedgerRead,
    BalanceSheetRead,
    GeneralLedgerRead,
    ProfitAndLossRead,
    TrialBalanceRead,
)


class ReportCsvRenderer(Protocol):
    """Produces UTF-8 CSV text (with BOM) from application report DTOs."""

    def trial_balance(self, report: TrialBalanceRead) -> str: ...
    def profit_and_loss(self, report: ProfitAndLossRead) -> str: ...
    def balance_sheet(self, report: BalanceSheetRead) -> str: ...
    def account_ledger(self, report: AccountLedgerRead) -> str: ...
    def general_ledger(self, report: GeneralLedgerRead) -> str: ...


class ReportPdfRenderer(Protocol):
    """Produces PDF bytes from application report DTOs."""

    def trial_balance(self, report: TrialBalanceRead) -> bytes: ...
    def profit_and_loss(self, report: ProfitAndLossRead) -> bytes: ...
    def balance_sheet(self, report: BalanceSheetRead) -> bytes: ...
    def account_ledger(self, report: AccountLedgerRead) -> bytes: ...
    def general_ledger(self, report: GeneralLedgerRead) -> bytes: ...
