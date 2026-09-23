from __future__ import annotations

"""Application ports for credit/debit note persistence."""

from typing import Protocol

from app.application.credit_notes.dto import (
    AllocateCreditNoteCommand,
    CreateCreditNoteCommand,
    CreditNoteDTO,
    CreditNotePageDTO,
    CreditNoteQuery,
    PostCreditNoteCommand,
    VoidCreditNoteCommand,
)


class CreditNoteRepository(Protocol):
    def create(self, command: CreateCreditNoteCommand) -> CreditNoteDTO:
        ...

    def get_by_id(self, credit_note_id: int) -> CreditNoteDTO | None:
        ...

    def get_by_no(
        self,
        company_id: int,
        note_type: str,
        credit_note_no: str,
    ) -> CreditNoteDTO | None:
        ...

    def list(self, query: CreditNoteQuery) -> CreditNotePageDTO:
        ...

    def post(self, command: PostCreditNoteCommand) -> CreditNoteDTO:
        ...

    def void(self, command: VoidCreditNoteCommand) -> CreditNoteDTO:
        ...

    def allocate(self, command: AllocateCreditNoteCommand) -> CreditNoteDTO:
        ...
