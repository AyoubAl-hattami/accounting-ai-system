"""Subscription repository port.

Defined as ``typing.Protocol`` — never ABC — so the application layer remains
framework-neutral.
"""

from __future__ import annotations

from typing import Protocol

from app.application.subscriptions.dto import (
    CompanySubscriptionDTO,
    SubscriptionDTO,
    UpdateSubscriptionCommand,
)


class SubscriptionRepository(Protocol):
    def get(self, company_id: int) -> SubscriptionDTO | None: ...

    def get_or_create(self, company_id: int) -> SubscriptionDTO: ...

    def update(self, command: UpdateSubscriptionCommand) -> SubscriptionDTO: ...

    def list_companies(
        self,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
        newest_first: bool = False,
    ) -> list[CompanySubscriptionDTO]: ...

    def count_companies(self, *, search: str | None = None) -> int: ...

    def get_company_summary(self, company_id: int) -> CompanySubscriptionDTO | None: ...
