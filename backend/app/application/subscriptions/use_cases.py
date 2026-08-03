"""Subscription application use cases.

Every mutating use case is platform-admin territory; authorisation itself is
enforced at the route boundary, so these stay purely about subscription state.
"""

from __future__ import annotations

from datetime import datetime

from app.application.subscriptions.dto import (
    CompanySubscriptionDTO,
    CompanySubscriptionPageDTO,
    SubscriptionDTO,
    UpdateSubscriptionCommand,
)
from app.application.subscriptions.policy import (
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_SUSPENDED,
    TERMINAL_STATUSES,
    extended_expiry,
    utc_now,
)
from app.application.subscriptions.ports import SubscriptionRepository

# The platform tenant list is small by nature; scanning it in one page keeps the
# derived-status filter correct without a materialised status column.
_UNFILTERED_SCAN_LIMIT = 1000


class ListCompanySubscriptions:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CompanySubscriptionPageDTO:
        # Effective status is derived, not stored, so a status filter cannot be
        # pushed into SQL without duplicating the expiry rule in two places.
        if status is None:
            items = self._repository.list_companies(search=search, skip=skip, limit=limit)
            total = self._repository.count_companies(search=search)
            return CompanySubscriptionPageDTO(
                items=tuple(items), total=total, skip=skip, limit=limit
            )

        matched = [
            item
            for item in self._repository.list_companies(
                search=search, skip=0, limit=_UNFILTERED_SCAN_LIMIT
            )
            if item.effective_status == status
        ]
        return CompanySubscriptionPageDTO(
            items=tuple(matched[skip : skip + limit]),
            total=len(matched),
            skip=skip,
            limit=limit,
        )


class GetCompanySubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int) -> CompanySubscriptionDTO | None:
        return self._repository.get_company_summary(company_id)


class UpdateSubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateSubscriptionCommand) -> SubscriptionDTO:
        self._repository.get_or_create(command.company_id)

        fields = set(command.fields)
        values: dict[str, object] = {
            field: getattr(command, field) for field in fields
        }

        # Keep the lifecycle timestamps consistent with whatever status the
        # admin just chose, so the audit trail never contradicts itself.
        if "status" in fields:
            now = utc_now()
            if command.status == STATUS_SUSPENDED:
                values.setdefault("suspended_at", now)
            elif command.status == STATUS_CANCELLED:
                values.setdefault("cancelled_at", now)
            else:
                values["suspended_at"] = None
                values["cancelled_at"] = None
                values.setdefault("suspension_reason", None)

        return self._repository.update(
            UpdateSubscriptionCommand(
                company_id=command.company_id,
                fields=frozenset(values.keys()),
                **values,  # type: ignore[arg-type]
            )
        )


class ExtendSubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        *,
        months: int = 0,
        years: int = 0,
        now: datetime | None = None,
    ) -> SubscriptionDTO:
        current = self._repository.get_or_create(company_id)
        expires_at = extended_expiry(
            current.expires_at, months=months, years=years, now=now
        )

        values: dict[str, object] = {"expires_at": expires_at}
        # Suspension and cancellation are deliberate admin decisions; buying more
        # time does not undo them. Everything else becomes active again.
        if current.status not in TERMINAL_STATUSES:
            values["status"] = STATUS_ACTIVE

        return self._repository.update(
            UpdateSubscriptionCommand(
                company_id=company_id,
                fields=frozenset(values.keys()),
                **values,  # type: ignore[arg-type]
            )
        )


class ActivateSubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        *,
        expires_at: datetime | None = None,
        plan_code: str | None = None,
    ) -> SubscriptionDTO:
        current = self._repository.get_or_create(company_id)

        values: dict[str, object] = {
            "status": STATUS_ACTIVE,
            "suspended_at": None,
            "cancelled_at": None,
            "suspension_reason": None,
            "expires_at": expires_at if expires_at is not None else current.expires_at,
        }
        if plan_code is not None:
            values["plan_code"] = plan_code

        return self._repository.update(
            UpdateSubscriptionCommand(
                company_id=company_id,
                fields=frozenset(values.keys()),
                **values,  # type: ignore[arg-type]
            )
        )


class SuspendSubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int, *, reason: str | None = None) -> SubscriptionDTO:
        self._repository.get_or_create(company_id)
        return self._repository.update(
            UpdateSubscriptionCommand(
                company_id=company_id,
                fields=frozenset({"status", "suspended_at", "suspension_reason"}),
                status=STATUS_SUSPENDED,
                suspended_at=utc_now(),
                suspension_reason=reason,
            )
        )


class CancelSubscription:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int, *, reason: str | None = None) -> SubscriptionDTO:
        self._repository.get_or_create(company_id)
        return self._repository.update(
            UpdateSubscriptionCommand(
                company_id=company_id,
                fields=frozenset({"status", "cancelled_at", "suspension_reason"}),
                status=STATUS_CANCELLED,
                cancelled_at=utc_now(),
                suspension_reason=reason,
            )
        )
