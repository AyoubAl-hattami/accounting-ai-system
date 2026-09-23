from __future__ import annotations

"""Application ports for invoice persistence."""

from typing import Protocol

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    InvoiceDTO,
    InvoicePageDTO,
    InvoiceQuery,
    PostInvoiceCommand,
    UpdateInvoiceCommand,
    VoidInvoiceCommand,
)


class InvoiceRepository(Protocol):
    def create(self, command: CreateInvoiceCommand) -> InvoiceDTO:
        ...

    def update(self, command: UpdateInvoiceCommand) -> InvoiceDTO:
        ...

    def get_by_id(self, invoice_id: int) -> InvoiceDTO | None:
        ...

    def get_by_no(
        self,
        company_id: int,
        invoice_type: str,
        invoice_no: str,
    ) -> InvoiceDTO | None:
        ...

    def list(self, query: InvoiceQuery) -> InvoicePageDTO:
        ...

    def post(self, command: PostInvoiceCommand) -> InvoiceDTO:
        ...

    def void(self, command: VoidInvoiceCommand) -> InvoiceDTO:
        ...

    def get_open_invoices(
        self,
        company_id: int,
        partner_id: int,
        currency: str | None = None,
    ) -> list[InvoiceDTO]:
        ...
