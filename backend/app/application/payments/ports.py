from __future__ import annotations

"""Application ports for payment persistence."""

from typing import Protocol

from app.application.payments.dto import (
    CreatePaymentCommand,
    PaymentDTO,
    PaymentPageDTO,
    PaymentQuery,
    PostPaymentCommand,
    VoidPaymentCommand,
)


class PaymentRepository(Protocol):
    def create(self, command: CreatePaymentCommand) -> PaymentDTO:
        ...

    def get_by_id(self, payment_id: int) -> PaymentDTO | None:
        ...

    def list(self, query: PaymentQuery) -> PaymentPageDTO:
        ...

    def post(self, command: PostPaymentCommand) -> PaymentDTO:
        ...

    def void(self, command: VoidPaymentCommand) -> PaymentDTO:
        ...
