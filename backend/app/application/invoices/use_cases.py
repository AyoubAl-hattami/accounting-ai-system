"""Invoice application use cases."""

from dataclasses import replace

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    InvoiceDTO,
    InvoicePageDTO,
    InvoiceQuery,
    PostInvoiceCommand,
    UpdateInvoiceCommand,
    VoidInvoiceCommand,
)
from app.application.invoices.ports import InvoiceRepository


class CreateInvoice:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateInvoiceCommand) -> InvoiceDTO:
        normalized = replace(
            command,
            invoice_no=command.invoice_no.strip(),
            currency=command.currency.strip().upper(),
            reference=command.reference.strip() if command.reference else None,
        )
        return self._repository.create(normalized)


class UpdateInvoice:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateInvoiceCommand) -> InvoiceDTO:
        return self._repository.update(command)


class GetInvoice:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, invoice_id: int) -> InvoiceDTO | None:
        return self._repository.get_by_id(invoice_id)


class ListInvoices:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, query: InvoiceQuery) -> InvoicePageDTO:
        return self._repository.list(query)


class PostInvoice:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, command: PostInvoiceCommand) -> InvoiceDTO:
        return self._repository.post(command)


class VoidInvoice:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(self, command: VoidInvoiceCommand) -> InvoiceDTO:
        return self._repository.void(command)


class GetOpenInvoices:
    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        partner_id: int,
        currency: str | None = None,
    ) -> list[InvoiceDTO]:
        return self._repository.get_open_invoices(
            company_id=company_id,
            partner_id=partner_id,
            currency=currency,
        )
