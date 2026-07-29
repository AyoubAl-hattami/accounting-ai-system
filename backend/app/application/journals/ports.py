"""Application port for journal persistence."""

from typing import Protocol

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    JournalEntryDTO,
    UpdateJournalEntryCommand,
)


class JournalRepository(Protocol):
    def create(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        ...

    def update(self, command: UpdateJournalEntryCommand) -> JournalEntryDTO:
        ...

    def get_by_id(self, journal_entry_id: int) -> JournalEntryDTO | None:
        ...

    def list_by_company(
        self,
        company_id: int,
        status: str | None,
        skip: int,
        limit: int,
    ) -> list[JournalEntryDTO]:
        ...

    def count_by_company(
        self,
        company_id: int,
        status: str | None,
    ) -> int:
        ...
