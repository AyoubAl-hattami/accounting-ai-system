"""Application port for journal persistence."""

from typing import Protocol

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateOpeningBalanceCommand,
    JournalEntryDTO,
    PostJournalEntryCommand,
    ReviewJournalEntryCommand,
    ReverseJournalEntryCommand,
    UpdateJournalEntryCommand,
    VoidJournalEntryCommand,
)


class JournalRepository(Protocol):
    def create(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        ...

    def create_opening_balance(
        self, command: CreateOpeningBalanceCommand
    ) -> JournalEntryDTO:
        ...

    def update(self, command: UpdateJournalEntryCommand) -> JournalEntryDTO:
        ...

    def review(self, command: ReviewJournalEntryCommand) -> JournalEntryDTO:
        ...

    def post(self, command: PostJournalEntryCommand) -> JournalEntryDTO:
        ...

    def void(self, command: VoidJournalEntryCommand) -> JournalEntryDTO:
        ...

    def reverse(self, command: ReverseJournalEntryCommand) -> JournalEntryDTO:
        ...

    def get_by_id(self, journal_entry_id: int) -> JournalEntryDTO | None:
        ...

    def get_by_entry_no(
        self,
        company_id: int,
        entry_no: str,
    ) -> JournalEntryDTO | None:
        ...

    def get_reversal_by_original_id(
        self,
        original_entry_id: int,
    ) -> JournalEntryDTO | None:
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

    def count_by_fiscal_year(self, fiscal_year_id: int) -> int:
        ...
