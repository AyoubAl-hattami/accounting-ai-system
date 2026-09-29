"""Payment application use cases."""

from dataclasses import replace

from app.application.payments.dto import (
    CreatePaymentCommand,
    PaymentDTO,
    PaymentPageDTO,
    PaymentQuery,
    PostPaymentCommand,
    VoidPaymentCommand,
)
from app.application.payments.ports import PaymentRepository


class CreatePayment:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def execute(self, command: CreatePaymentCommand) -> PaymentDTO:
        normalized = replace(
            command,
            currency_code=command.currency_code.strip().upper(),
            reference=command.reference.strip() if command.reference else None,
            memo=command.memo.strip() if command.memo else None,
        )
        return self._repository.create(normalized)


class GetPayment:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def execute(self, payment_id: int) -> PaymentDTO | None:
        return self._repository.get_by_id(payment_id)


class ListPayments:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def execute(self, query: PaymentQuery) -> PaymentPageDTO:
        return self._repository.list(query)


class PostPayment:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def execute(self, command: PostPaymentCommand) -> PaymentDTO:
        return self._repository.post(command)


class VoidPayment:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def execute(self, command: VoidPaymentCommand) -> PaymentDTO:
        return self._repository.void(command)
