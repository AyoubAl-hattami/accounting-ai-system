"""Application use cases for credit and debit note workflows."""

from __future__ import annotations

from app.application.credit_notes.dto import (
    AllocateCreditNoteCommand,
    CreateCreditNoteCommand,
    CreditNoteDTO,
    CreditNotePageDTO,
    CreditNoteQuery,
    PostCreditNoteCommand,
    VoidCreditNoteCommand,
)
from app.application.credit_notes.ports import CreditNoteRepository


class CreateCreditNote:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateCreditNoteCommand) -> CreditNoteDTO:
        return self._repository.create(command)


class GetCreditNote:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, credit_note_id: int) -> CreditNoteDTO | None:
        return self._repository.get_by_id(credit_note_id)


class ListCreditNotes:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, query: CreditNoteQuery) -> CreditNotePageDTO:
        return self._repository.list(query)


class PostCreditNote:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, command: PostCreditNoteCommand) -> CreditNoteDTO:
        return self._repository.post(command)


class VoidCreditNote:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, command: VoidCreditNoteCommand) -> CreditNoteDTO:
        return self._repository.void(command)


class AllocateCreditNote:
    def __init__(self, repository: CreditNoteRepository) -> None:
        self._repository = repository

    def execute(self, command: AllocateCreditNoteCommand) -> CreditNoteDTO:
        return self._repository.allocate(command)
