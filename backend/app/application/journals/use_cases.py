"""Journal application use cases."""

from dataclasses import replace
from decimal import Decimal

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateOpeningBalanceCommand,
    JournalEntryDTO,
    JournalEntryPageDTO,
    PostJournalEntryCommand,
    ReviewJournalEntryCommand,
    ReverseJournalEntryCommand,
    UpdateJournalEntryCommand,
    VoidJournalEntryCommand,
)
from app.application.journals.ports import JournalRepository


class CreateJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        normalized_command = replace(command, entry_no=command.entry_no.strip())
        return self._repository.create(normalized_command)


class CreateOpeningBalance:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateOpeningBalanceCommand) -> JournalEntryDTO:
        normalized_command = replace(command, entry_no=command.entry_no.strip())
        return self._repository.create_opening_balance(normalized_command)


class UpdateJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateJournalEntryCommand) -> JournalEntryDTO:
        return self._repository.update(command)


class ReviewJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: ReviewJournalEntryCommand) -> JournalEntryDTO:
        return self._repository.review(command)


class PostJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: PostJournalEntryCommand) -> JournalEntryDTO:
        return self._repository.post(command)


class VoidJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: VoidJournalEntryCommand) -> JournalEntryDTO:
        return self._repository.void(command)


class ReverseJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: ReverseJournalEntryCommand) -> JournalEntryDTO:
        normalized_command = replace(command, entry_no=command.entry_no.strip())
        return self._repository.reverse(normalized_command)


class GetJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, journal_entry_id: int) -> JournalEntryDTO | None:
        return self._repository.get_by_id(journal_entry_id)


class GetJournalEntryByNo:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        entry_no: str,
    ) -> JournalEntryDTO | None:
        return self._repository.get_by_entry_no(company_id, entry_no.strip())


class ListJournalEntries:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        status: str | None,
        skip: int,
        limit: int,
    ) -> JournalEntryPageDTO:
        return JournalEntryPageDTO(
            items=self._repository.list_by_company(
                company_id=company_id,
                status=status,
                skip=skip,
                limit=limit,
            ),
            total=self._repository.count_by_company(
                company_id=company_id,
                status=status,
            ),
            skip=skip,
            limit=limit,
        )


class CountJournalEntries:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        status: str | None = None,
    ) -> int:
        return self._repository.count_by_company(
            company_id=company_id,
            status=status,
        )


def calculate_journal_totals(
    journal_entry: JournalEntryDTO,
) -> tuple[Decimal, Decimal]:
    total_debit = sum((line.debit for line in journal_entry.lines), Decimal("0"))
    total_credit = sum((line.credit for line in journal_entry.lines), Decimal("0"))
    return total_debit, total_credit
