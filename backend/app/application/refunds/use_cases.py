"""Application use cases for refund workflows."""

from __future__ import annotations

from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
    RefundDTO,
    RefundPageDTO,
    RefundQuery,
    VoidRefundCommand,
)
from app.application.refunds.ports import RefundRepository


class CreateRefund:
    def __init__(self, repository: RefundRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateRefundCommand) -> RefundDTO:
        return self._repository.create(command)


class GetRefund:
    def __init__(self, repository: RefundRepository) -> None:
        self._repository = repository

    def execute(self, refund_id: int) -> RefundDTO | None:
        return self._repository.get_by_id(refund_id)


class ListRefunds:
    def __init__(self, repository: RefundRepository) -> None:
        self._repository = repository

    def execute(self, query: RefundQuery) -> RefundPageDTO:
        return self._repository.list(query)


class PostRefund:
    def __init__(self, repository: RefundRepository) -> None:
        self._repository = repository

    def execute(self, command: PostRefundCommand) -> RefundDTO:
        return self._repository.post(command)


class VoidRefund:
    def __init__(self, repository: RefundRepository) -> None:
        self._repository = repository

    def execute(self, command: VoidRefundCommand) -> RefundDTO:
        return self._repository.void(command)
