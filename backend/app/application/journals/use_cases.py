"""Journal application use cases."""

from dataclasses import replace

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    JournalEntryDTO,
    JournalEntryPageDTO,
)
from app.application.journals.ports import JournalRepository


class CreateJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        normalized_command = replace(command, entry_no=command.entry_no.strip())
        return self._repository.create(normalized_command)


class GetJournalEntry:
    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def execute(self, journal_entry_id: int) -> JournalEntryDTO | None:
        return self._repository.get_by_id(journal_entry_id)


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
