from datetime import date, datetime, timezone
from decimal import Decimal

from app.application.journals.dto import (
    CreateJournalLineCommand,
    CreateOpeningBalanceCommand,
    JournalEntryDTO,
)
from app.application.journals.use_cases import CreateOpeningBalance


class RecordingRepository:
    def __init__(self, result):
        self.result = result
        self.command = None

    def create_opening_balance(self, command):
        self.command = command
        return self.result


def test_create_opening_balance_trims_number_and_delegates_exact_command():
    now = datetime.now(timezone.utc)
    expected = JournalEntryDTO(
        id=51, company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="OB-51", entry_date=date(2026, 1, 1),
        description="Opening balances", status="draft",
        source_type="opening_balance", source_id=None,
        created_by_user_id=7, creator_name="Creator", reversal_of_id=None,
        posted_at=None, created_at=now, updated_at=now, lines=[],
    )
    lines = (
        CreateJournalLineCommand(10, Decimal("60.00"), Decimal("0.00"), "debit"),
        CreateJournalLineCommand(20, Decimal("0.00"), Decimal("60.00"), "credit"),
    )
    command = CreateOpeningBalanceCommand(
        company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="  OB-51  ", entry_date=date(2026, 1, 1),
        description="Opening balances", created_by_user_id=7, lines=lines,
    )
    repository = RecordingRepository(expected)

    result = CreateOpeningBalance(repository).execute(command)

    assert result is expected
    assert repository.command == CreateOpeningBalanceCommand(
        company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="OB-51", entry_date=date(2026, 1, 1),
        description="Opening balances", created_by_user_id=7, lines=lines,
    )
    assert command.entry_no == "  OB-51  "