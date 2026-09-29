from __future__ import annotations

"""Application ports for refund persistence."""

from typing import Protocol

from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
    RefundDTO,
    RefundPageDTO,
    RefundQuery,
    VoidRefundCommand,
)


class RefundRepository(Protocol):
    def create(self, command: CreateRefundCommand) -> RefundDTO:
        ...

    def get_by_id(self, refund_id: int) -> RefundDTO | None:
        ...

    def list(self, query: RefundQuery) -> RefundPageDTO:
        ...

    def post(self, command: PostRefundCommand) -> RefundDTO:
        ...

    def void(self, command: VoidRefundCommand) -> RefundDTO:
        ...
